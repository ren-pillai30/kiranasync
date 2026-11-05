import math
import os

from flask import jsonify, request
from flask_login import LoginManager, current_user, login_user, logout_user
from sqlalchemy.exc import OperationalError

from backend.app.database import db
from backend.app.models import Store, User
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
