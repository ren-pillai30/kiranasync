import math
import os
import sqlite3

from flask import jsonify, request, session
from flask_login import LoginManager, current_user, login_user, logout_user
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from backend.app.database import db, is_postgres_database
from backend.app.models import (
    Store,
    StoreCredit,
    StoreEntityArchive,
    StoreInventory,
    StoreTransaction,
    User,
)
from backend.app.intent_parser import initialize_store_database


login_manager = LoginManager()
login_manager.login_view = None


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except OperationalError:
        db.session.rollback()
        return db.session.get(User, int(user_id))


def register_auth_routes(app):
    @app.route("/api/auth/session", methods=["GET"])
    def auth_session():
        if not current_user.is_authenticated:
            return jsonify({"status": "unauthenticated"}), 401
        return jsonify({
            "status": "success",
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "display_name": current_user.display_name,
                "role": current_user.role,
                "store_id": current_user.store_id,
                "store_name": current_user.store.name,
                "store_setup_complete": current_user.store.setup_complete,
                "store_phone": current_user.store.phone,
                "store_address": current_user.store.address,
                "store_city": current_user.store.city,
                "register_opening_balance": current_user.store.register_opening_balance,
            },
        })

    @app.route("/api/auth/login", methods=["POST"])
    def auth_login():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email") or "").strip().lower()
        password = str(data.get("password") or "")
        user = db.session.execute(
            db.select(User).where(db.func.lower(User.email) == email)
        ).scalar_one_or_none()
        if not user or not user.is_active or not user.check_password(password):
            return jsonify({"status": "error", "error": "Invalid email or password."}), 401
        if not user.store.is_active:
            return jsonify({"status": "error", "error": "This store is unavailable."}), 403
        login_user(user, remember=False)
        return jsonify({
            "status": "success",
            "user": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "role": user.role,
                "store_id": user.store_id,
                "store_name": user.store.name,
                "store_setup_complete": user.store.setup_complete,
                "store_phone": user.store.phone,
                "store_address": user.store.address,
                "store_city": user.store.city,
                "register_opening_balance": user.store.register_opening_balance,
            },
        })

    @app.route("/api/auth/logout", methods=["POST"])
    def auth_logout():
        logout_user()
        return jsonify({"status": "success"})

    @app.route("/api/auth/register", methods=["POST"])
    def auth_register():
        public_registration = os.getenv("ALLOW_PUBLIC_REGISTRATION", "").strip().lower() in {"1", "true", "yes"}
        if User.query.first() is not None and not public_registration:
            return jsonify({"status": "error", "error": "Registration is disabled."}), 403

        data = request.get_json(silent=True) or {}
        store_name = str(data.get("store_name") or "").strip()
        display_name = str(data.get("display_name") or "").strip()
        email = str(data.get("email") or "").strip().lower()
        password = str(data.get("password") or "")
        if not store_name or not display_name or not email or len(password) < 10:
            return jsonify({
                "status": "error",
                "error": "Store name, display name, email, and a 10-character password are required.",
            }), 400
        if User.query.filter(db.func.lower(User.email) == email).first():
            return jsonify({"status": "error", "error": "An account with this email already exists."}), 409

        store = Store(name=store_name)
        user = User(store=store, email=email, display_name=display_name, role="owner")
        user.set_password(password)
        db.session.add_all([store, user])
        db.session.commit()
        initialize_store_database(store.id)
        login_user(user, remember=False)
        return jsonify({"status": "success", "store_id": store.id, "user_id": user.id})

    @app.route("/api/store/setup", methods=["POST"])
    def complete_store_setup():
        if not current_user.is_authenticated:
            return jsonify({"status": "error", "error": "Authentication required."}), 401
        data = request.get_json(silent=True) or {}
        store_name = str(data.get("store_name") or "").strip()
        phone = str(data.get("phone") or "").strip()
        address = str(data.get("address") or "").strip()
        city = str(data.get("city") or "").strip()
        try:
            register_opening_balance = float(data.get("register_opening_balance"))
        except (TypeError, ValueError):
            return jsonify({
                "status": "error",
                "error": "Enter a valid opening register amount.",
            }), 400
        if not math.isfinite(register_opening_balance) or register_opening_balance < 0:
            return jsonify({
                "status": "error",
                "error": "Opening register amount must be zero or more.",
            }), 400
        if not store_name or not phone or not address or not city:
            return jsonify({
                "status": "error",
                "error": "Store name, phone number, address, and city are required.",
            }), 400
        current_user.store.name = store_name
        current_user.store.phone = phone
        current_user.store.address = address
        current_user.store.city = city
        current_user.store.register_opening_balance = register_opening_balance
        current_user.store.setup_complete = True
        db.session.commit()
        return jsonify({
            "status": "success",
            "store": {
                "store_name": store_name,
                "phone": phone,
                "address": address,
                "city": city,
                "register_opening_balance": register_opening_balance,
                "setup_complete": True,
            },
        })

    @app.route("/api/store/reset", methods=["POST"])
    def reset_store():
        if not current_user.is_authenticated:
            return jsonify({"status": "error", "error": "Authentication required."}), 401
        if (
            current_user.email.casefold() != "aryan.pillai2024@vitstudent.ac.in"
            or current_user.role != "owner"
        ):
            return jsonify({"status": "error", "error": "This action is not available for this account."}), 403
        data = request.get_json(silent=True) or {}
        if data.get("confirmation") != "RESET":
            return jsonify({"status": "error", "error": "Type RESET to confirm clearing this store."}), 400

        store = current_user.store
        try:
            if is_postgres_database():
                store_id = current_user.store_id
                for model in (
                    StoreInventory,
                    StoreCredit,
                    StoreTransaction,
                    StoreEntityArchive,
                ):
                    model.query.filter_by(store_id=store_id).delete(
                        synchronize_session=False
                    )

            store.name = "My Store"
            store.phone = None
            store.address = None
            store.city = None
            store.register_opening_balance = 0
            store.setup_complete = False

            from backend.app.intent_parser import get_store_db_path, initialize_store_database

            database_path = get_store_db_path(current_user.store_id)
            if not os.path.exists(database_path):
                initialize_store_database(current_user.store_id)
            connection = sqlite3.connect(database_path)
            try:
                with connection:
                    existing_tables = {
                        row[0]
                        for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type = 'table'"
                        )
                    }
                    for table in (
                        "Inventory",
                        "CustomerCredit",
                        "Transactions",
                        "EntityArchive",
                        "Aliases",
                        "PendingCommands",
                    ):
                        if table in existing_tables:
                            connection.execute(f'DELETE FROM "{table}"')
                    if "sqlite_sequence" in existing_tables:
                        connection.execute(
                            """
                            DELETE FROM sqlite_sequence
                            WHERE name IN (
                                'Inventory', 'CustomerCredit', 'Transactions',
                                'EntityArchive', 'Aliases'
                            )
                            """
                        )
            finally:
                connection.close()
            db.session.commit()
        except (sqlite3.Error, OSError):
            db.session.rollback()
            app.logger.exception("Store data reset failed for store %s", current_user.store_id)
            return jsonify({
                "status": "error",
                "error": "The store data could not be fully reset. No reset was confirmed; contact support before retrying.",
            }), 500
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Store profile reset failed for store %s", current_user.store_id)
            return jsonify({
                "status": "error",
                "error": "Store data was cleared, but the store profile could not be reset. Contact support before continuing.",
            }), 500

        session.pop("call_sim_pending_action", None)
        session.pop("call_sim_bill_items", None)
        return jsonify({
            "status": "success",
            "store": {
                "store_name": store.name,
                "phone": store.phone,
                "address": store.address,
                "city": store.city,
                "register_opening_balance": store.register_opening_balance,
                "setup_complete": store.setup_complete,
            },
        })
