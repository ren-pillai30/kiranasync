import sqlite3

from backend.app.intent_parser import ensure_transactions_schema, record_transaction


class EntityService:
    def __init__(self, db_path):
        self.db_path = db_path

    def list_archives(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            ensure_transactions_schema(conn)
            rows = conn.execute(
                """
                SELECT ArchiveID, EntityType, EntityName, RemovalType,
                       RemovedAt, Reason, Quantity, Balance, RawCommand
                FROM EntityArchive
                ORDER BY RemovedAt DESC, ArchiveID DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def archive_inventory_item(self, item_id, reason=None, raw_command=None):
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            ensure_transactions_schema(conn)
            cursor = conn.cursor()
            inventory_columns = {
                row[1] for row in cursor.execute("PRAGMA table_info(Inventory)")
            }
            cost_column = "PurchaseCost" if "PurchaseCost" in inventory_columns else "Price"
            cursor.execute(
                f"SELECT ItemName, StockQuantity, Price, {cost_column} "
                "FROM Inventory WHERE ItemID = ? AND IsActive = 1",
                (item_id,),
            )
            item = cursor.fetchone()
            if not item:
                return {"status": "error", "error": "That active inventory item was not found."}

            item_name, stock_quantity, unit_price, purchase_cost = item
            unit_cost = purchase_cost if purchase_cost is not None else unit_price
            cursor.execute(
                "UPDATE Inventory SET IsActive = 0, StockQuantity = 0 WHERE ItemID = ? AND IsActive = 1",
                (item_id,),
            )
            if cursor.rowcount != 1:
                return {"status": "error", "error": "That inventory item was already removed."}

            reason_text = f" Reason: {reason.strip()}" if isinstance(reason, str) and reason.strip() else ""
            command_text = raw_command or f"Removed inventory item {item_name}"
            record_transaction(
                cursor,
                f"{command_text}{reason_text}",
                -float(unit_cost or 0) * int(stock_quantity or 0),
                "WriteOff",
                item_name,
                int(stock_quantity or 0),
            )
            transaction_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO EntityArchive (
                    SourceTransactionID, EntityType, EntityID, EntityName,
                    RemovalType, Reason, Quantity, RawCommand
                ) VALUES (?, 'Product', ?, ?, 'WriteOff', ?, ?, ?)
                """,
                (
                    transaction_id,
                    item_id,
                    item_name,
                    reason.strip() if isinstance(reason, str) and reason.strip() else None,
                    int(stock_quantity or 0),
                    raw_command,
                ),
            )
            conn.commit()
            return {
                "status": "success",
                "action": "inventory_archived",
                "message": (
                    f"Removed {item_name} from active inventory and recorded "
                    f"a write-off for {stock_quantity} unit(s)."
                ),
            }
        finally:
            conn.close()

    def archive_customer(self, customer_id, reason=None, raw_command=None):
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            ensure_transactions_schema(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT CustomerName, OutstandingBalance
                FROM CustomerCredit
                WHERE CustomerID = ? AND IsActive = 1
                """,
                (customer_id,),
            )
            customer = cursor.fetchone()
            if not customer:
                return {"status": "error", "error": "That active customer was not found."}

            customer_name, balance = customer
            is_zero_balance = float(balance or 0) == 0
            if is_zero_balance:
                from backend.app.services.alias_service import ensure_aliases_schema
                ensure_aliases_schema(conn)
                cursor.execute(
                    "DELETE FROM Aliases WHERE EntityType = 'Customer' AND EntityID = ?",
                    (customer_id,),
                )
                cursor.execute(
                    "DELETE FROM CustomerCredit WHERE CustomerID = ? AND IsActive = 1",
                    (customer_id,),
                )
            else:
                cursor.execute(
                    "UPDATE CustomerCredit SET IsActive = 0 WHERE CustomerID = ? AND IsActive = 1",
                    (customer_id,),
                )
            if cursor.rowcount != 1:
                return {"status": "error", "error": "That customer was already removed."}

            reason_text = f" Reason: {reason.strip()}" if isinstance(reason, str) and reason.strip() else ""
            record_transaction(
                cursor,
                f"{raw_command or f'Removed customer {customer_name}'}{reason_text}",
                0,
                "CustomerArchived",
                customer_name,
                None,
            )
            transaction_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO EntityArchive (
                    SourceTransactionID, EntityType, EntityID, EntityName,
                    RemovalType, Reason, Balance, RawCommand
                ) VALUES (?, 'Customer', ?, ?, 'CustomerArchived', ?, ?, ?)
                """,
                (
                    transaction_id,
                    customer_id,
                    customer_name,
                    reason.strip() if isinstance(reason, str) and reason.strip() else None,
                    float(balance or 0),
                    raw_command,
                ),
            )
            conn.commit()
            return {
                "status": "success",
                "action": "customer_deleted" if is_zero_balance else "customer_archived",
                "message": (
                    f"Removed {customer_name} and their zero balance from the customer table. "
                    "Transaction history was retained."
                    if is_zero_balance
                    else
                    f"Removed {customer_name} from the active udhaar list. "
                    f"Their outstanding balance of Rs {float(balance or 0):g} and transaction history were retained."
                ),
            }
        finally:
            conn.close()
