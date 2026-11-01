import os
import sqlite3
import sys
import bcrypt

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def main():
    sqlite_path = os.getenv("SOURCE_SQLITE_PATH", "kirana.db")
    postgres_url = os.getenv("DATABASE_URL")
    store_name = os.getenv("MIGRATION_STORE_NAME", "My Store")
    owner_email = os.getenv("MIGRATION_OWNER_EMAIL", "").strip().lower()
    owner_password = os.getenv("MIGRATION_OWNER_PASSWORD", "")

    if not postgres_url:
        raise SystemExit("DATABASE_URL is required.")
    if not os.path.exists(sqlite_path):
        raise SystemExit(f"SQLite database not found: {sqlite_path}")
    if not owner_email:
        raise SystemExit("MIGRATION_OWNER_EMAIL is required.")
    if len(owner_password) < 10:
        raise SystemExit("MIGRATION_OWNER_PASSWORD must contain at least 10 characters.")

    url = make_url(postgres_url)
    if url.drivername in {"postgresql", "postgres"}:
        postgres_url = postgres_url.replace("postgresql://", "postgresql+psycopg://", 1)
        postgres_url = postgres_url.replace("postgres://", "postgresql+psycopg://", 1)

    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row
    target = create_engine(postgres_url, future=True).connect()
    with target.begin() as transaction:
        transaction.connection.execute(text("""
            CREATE TABLE IF NOT EXISTS stores (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT TRUE
            )
        """))
        transaction.connection.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
                email TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'owner',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """.replace("NOT NOT NULL", "NOT NULL")))
        store_result = transaction.connection.execute(
            text("""
                INSERT INTO stores (name, is_active, created_at)
                SELECT :name, true, CURRENT_TIMESTAMP
                WHERE NOT EXISTS (SELECT 1 FROM stores WHERE name = :name)
                RETURNING id
            """),
            {"name": store_name},
        )
        store_row = store_result.first()
        if store_row:
            store_id = store_row[0]
        else:
            store_id = transaction.connection.execute(
                text("SELECT id FROM stores WHERE name = :name ORDER BY id LIMIT 1"),
                {"name": store_name},
            ).scalar_one()
        transaction.connection.execute(text("""
            CREATE TABLE IF NOT EXISTS Inventory (
                ItemID BIGSERIAL PRIMARY KEY,
                StoreID INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
                ItemName TEXT NOT NULL,
                Category TEXT,
                StockQuantity REAL NOT NULL DEFAULT 0,
                Price REAL NOT NULL DEFAULT 0,
                SellingPrice REAL,
                MRP REAL,
                PurchaseCost REAL,
                Unit TEXT DEFAULT 'packet',
                ReorderLevel INTEGER DEFAULT 5,
                IsActive BOOLEAN NOT NOT NULL DEFAULT TRUE,
                UNIQUE (StoreID, ItemName)
            )
        """.replace("NOT NOT NULL", "NOT NULL")))
        transaction.connection.execute(text("""
            CREATE TABLE IF NOT EXISTS CustomerCredit (
                CustomerID BIGSERIAL PRIMARY KEY,
                StoreID INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
                CustomerName TEXT NOT NULL,
                PhoneNumber TEXT,
                OutstandingBalance REAL DEFAULT 0,
                IsActive BOOLEAN NOT NULL DEFAULT TRUE,
                UNIQUE (StoreID, CustomerName)
            )
        """))
        transaction.connection.execute(text("""
            CREATE TABLE IF NOT EXISTS Transactions (
                TxnID BIGSERIAL PRIMARY KEY,
                StoreID INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
                Timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CommandText TEXT,
                TotalAmount REAL,
                TransactionType TEXT,
                EntityName TEXT,
                Quantity REAL,
                CustomerID BIGINT,
                CommandID TEXT,
                IsReversed BOOLEAN DEFAULT FALSE
            )
        """))

        counts = {}
        inventory_rows = source.execute("SELECT * FROM Inventory").fetchall() if source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='Inventory'"
        ).fetchone() else []
        counts["Inventory"] = len(inventory_rows)
        for row in inventory_rows:
            values = dict(row)
            transaction.connection.execute(text("""
                INSERT INTO Inventory (
                    StoreID, ItemName, Category, StockQuantity, Price,
                    SellingPrice, MRP, PurchaseCost, Unit, ReorderLevel, IsActive
                ) VALUES (
                    :store_id, :item_name, :category, :stock, :price,
                    :selling_price, :mrp, :purchase_cost, :unit, :reorder, :is_active
                )
                ON CONFLICT (StoreID, ItemName) DO UPDATE
                SET StockQuantity = EXCLUDED.StockQuantity,
                    Price = EXCLUDED.Price,
                    IsActive = EXCLUDED.IsActive
            """), {
                "store_id": store_id,
                "item_name": values["ItemName"],
                "category": values.get("Category"),
                "stock": values.get("StockQuantity", 0),
                "price": values.get("Price", 0),
                "selling_price": values.get("SellingPrice"),
                "mrp": values.get("MRP"),
                "purchase_cost": values.get("PurchaseCost"),
                "unit": values.get("Unit", "packet"),
                "reorder": values.get("ReorderLevel", 5),
                "is_active": bool(values.get("IsActive", 1)),
            })

        customer_rows = source.execute("SELECT * FROM CustomerCredit").fetchall() if source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='CustomerCredit'"
        ).fetchone() else []
        counts["CustomerCredit"] = len(customer_rows)
        for row in customer_rows:
            values = dict(row)
            transaction.connection.execute(text("""
                INSERT INTO CustomerCredit (
                    StoreID, CustomerName, PhoneNumber, OutstandingBalance, IsActive
                ) VALUES (:store_id, :name, :phone, :balance, :is_active)
                ON CONFLICT (StoreID, CustomerName) DO UPDATE
                SET PhoneNumber = EXCLUDED.PhoneNumber,
                    OutstandingBalance = EXCLUDED.OutstandingBalance,
                    IsActive = EXCLUDED.IsActive
            """), {
                "store_id": store_id,
                "name": values["CustomerName"],
                "phone": values.get("PhoneNumber"),
                "balance": values.get("OutstandingBalance", 0),
                "is_active": bool(values.get("IsActive", 1)),
            })

        transaction_rows = source.execute("SELECT * FROM Transactions").fetchall() if source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='Transactions'"
        ).fetchone() else []
        counts["Transactions"] = len(transaction_rows)
        for row in transaction_rows:
            values = dict(row)
            transaction.connection.execute(text("""
                INSERT INTO Transactions (
                    StoreID, Timestamp, CommandText, TotalAmount, TransactionType,
                    EntityName, Quantity, CommandID, IsReversed
                ) VALUES (
                    :store_id, COALESCE(:timestamp, CURRENT_TIMESTAMP), :command,
                    :total, :type, :entity, :quantity, :command_id, :is_reversed
                )
            """), {
                "store_id": store_id,
                "timestamp": values.get("Timestamp") or None,
                "command": values.get("CommandText"),
                "total": values.get("TotalAmount"),
                "type": values.get("TransactionType"),
                "entity": values.get("EntityName"),
                "quantity": values.get("Quantity"),
                "command_id": values.get("CommandID"),
                "is_reversed": bool(values.get("IsReversed", 0)),
            })

        owner_hash = bcrypt.hashpw(owner_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        transaction.connection.execute(text("""
            INSERT INTO users (store_id, email, display_name, password_hash, role, is_active, created_at)
            VALUES (:store_id, :email, 'Store Owner', :password_hash, 'owner', true, CURRENT_TIMESTAMP)
            ON CONFLICT (email) DO UPDATE SET store_id = EXCLUDED.store_id, is_active = true
        """), {"store_id": store_id, "email": owner_email, "password_hash": owner_hash})

        print(f"Migrated store ID: {store_id}")
        print(f"SQLite row counts: {counts}")
        print(f"Owner email: {owner_email}")
    target.commit()
    target.close()
    source.close()


if __name__ == "__main__":
    main()
