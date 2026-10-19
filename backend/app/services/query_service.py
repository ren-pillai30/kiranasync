import sqlite3
from datetime import datetime, timezone

def ensure_v2_schema(conn):
    """
    Safely migrates SQLite schema to KiranaSync 2.0 without losing historical data.
    - Adds SellingPrice, MRP, PurchaseCost, Unit, ReorderLevel to Inventory if not present.
    - Preserves existing 'Price' column as default SellingPrice.
    """
    cursor = conn.cursor()
    
    # 1. Update Inventory columns
    cursor.execute("PRAGMA table_info(Inventory)")
    inv_cols = {col[1] for col in cursor.fetchall()}
    
    if "SellingPrice" not in inv_cols:
        cursor.execute("ALTER TABLE Inventory ADD COLUMN SellingPrice REAL")
        cursor.execute("UPDATE Inventory SET SellingPrice = Price WHERE SellingPrice IS NULL")
    if "MRP" not in inv_cols:
        cursor.execute("ALTER TABLE Inventory ADD COLUMN MRP REAL")
    if "PurchaseCost" not in inv_cols:
        cursor.execute("ALTER TABLE Inventory ADD COLUMN PurchaseCost REAL")
    if "Unit" not in inv_cols:
        cursor.execute("ALTER TABLE Inventory ADD COLUMN Unit TEXT DEFAULT 'packet'")
    if "ReorderLevel" not in inv_cols:
        cursor.execute("ALTER TABLE Inventory ADD COLUMN ReorderLevel INTEGER DEFAULT 5")
        
    # 2. Update Transactions columns for udhaar_sale and repayment linkage
    cursor.execute("PRAGMA table_info(Transactions)")
    txn_cols = {col[1] for col in cursor.fetchall()}
    if "CustomerID" not in txn_cols:
        cursor.execute("ALTER TABLE Transactions ADD COLUMN CustomerID INTEGER")
    if "CommandID" not in txn_cols:
        cursor.execute("ALTER TABLE Transactions ADD COLUMN CommandID TEXT")
    if "IsReversed" not in txn_cols:
        cursor.execute("ALTER TABLE Transactions ADD COLUMN IsReversed INTEGER DEFAULT 0")

    conn.commit()

class QueryService:
    def __init__(self, db_path):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        ensure_v2_schema(conn)
        return conn

    def get_customer_balance(self, customer_name):
        """Query outstanding debt balance for a specific customer."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT CustomerID, CustomerName, OutstandingBalance FROM CustomerCredit WHERE CustomerName LIKE ?",
                (f"%{customer_name.strip()}%",)
            )
            rows = cursor.fetchall()
            if not rows:
                return {"found": False, "message": f"Customer '{customer_name}' not found."}
            if len(rows) > 1:
                return {
                    "found": True,
                    "ambiguous": True,
                    "matches": [{"CustomerID": r["CustomerID"], "CustomerName": r["CustomerName"]} for r in rows],
                    "message": f"Multiple customers found matching '{customer_name}'."
                }
            r = rows[0]
            bal = float(r["OutstandingBalance"])
            return {
                "found": True,
                "ambiguous": False,
                "CustomerID": r["CustomerID"],
                "CustomerName": r["CustomerName"],
                "OutstandingBalance": bal,
                "message": f"{r['CustomerName']} has an outstanding balance of ₹{bal:g}."
            }
        finally:
            conn.close()

    def get_inventory_stock(self, item_name):
        """Query in-stock quantity and selling price for a specific product."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ItemID, ItemName, StockQuantity, coalesce(SellingPrice, Price) as SellingPrice, MRP FROM Inventory WHERE ItemName LIKE ?",
                (f"%{item_name.strip()}%",)
            )
            rows = cursor.fetchall()
            if not rows:
                return {"found": False, "message": f"Item '{item_name}' not found in inventory."}
            if len(rows) > 1:
                return {
                    "found": True,
                    "ambiguous": True,
                    "matches": [{"ItemID": r["ItemID"], "ItemName": r["ItemName"], "Stock": r["StockQuantity"]} for r in rows],
                    "message": f"Multiple items found matching '{item_name}'."
                }
            r = rows[0]
            return {
                "found": True,
                "ambiguous": False,
                "ItemID": r["ItemID"],
                "ItemName": r["ItemName"],
                "StockQuantity": int(r["StockQuantity"]),
                "SellingPrice": float(r["SellingPrice"]),
                "MRP": float(r["MRP"]) if r["MRP"] is not None else None,
                "message": f"{r['ItemName']}: {r['StockQuantity']} in stock at ₹{float(r['SellingPrice']):g}."
            }
        finally:
            conn.close()

    def get_low_stock_items(self):
        """Query items whose stock is less than or equal to their ReorderLevel."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ItemID, ItemName, StockQuantity, ReorderLevel, coalesce(SellingPrice, Price) as Price
                FROM Inventory
                WHERE StockQuantity <= coalesce(ReorderLevel, 5)
                ORDER BY StockQuantity ASC
            ''')
            rows = cursor.fetchall()
            items = [
                {
                    "ItemID": r["ItemID"],
                    "ItemName": r["ItemName"],
                    "StockQuantity": int(r["StockQuantity"]),
                    "ReorderLevel": int(r["ReorderLevel"] or 5),
                    "Price": float(r["Price"])
                }
                for r in rows
            ]
            msg = f"{len(items)} item(s) running low on stock." if items else "All items have healthy stock levels."
            return {"items": items, "count": len(items), "message": msg}
        finally:
            conn.close()

    def get_today_hisaab(self):
        """
        Calculates today's retail accounting metrics purely from SQLite records.
        Distinguishes Cash Sales, Udhaar Sales, Debt Repayments, and Restock Spend.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Calculate metrics for current day (UTC/Local day boundary)
            cursor.execute('''
                SELECT 
                    TransactionType,
                    coalesce(sum(TotalAmount), 0.0) as TotalSum,
                    count(*) as TxnCount
                FROM Transactions
                WHERE date(Timestamp) = date('now')
                GROUP BY TransactionType
            ''')
            summary = {row["TransactionType"]: {"total": float(row["TotalSum"]), "count": int(row["TxnCount"])} for row in cursor.fetchall()}
            
            cash_sales = summary.get("Sale", {"total": 0.0, "count": 0})
            udhaar_sales = summary.get("UdhaarSale", {"total": 0.0, "count": 0})
            repayments = summary.get("Repayment", {"total": 0.0, "count": 0})
            restocks = summary.get("Restock", {"total": 0.0, "count": 0})

            # Total current outstanding debt across all customers
            cursor.execute("SELECT coalesce(sum(OutstandingBalance), 0.0) FROM CustomerCredit")
            total_debt = float(cursor.fetchone()[0])

            total_revenue = cash_sales["total"] + udhaar_sales["total"]
            cash_collected = cash_sales["total"] + repayments["total"]

            message = (
                f"Today's Hisaab: Total Sales ₹{total_revenue:g} (Cash: ₹{cash_sales['total']:g}, Udhaar: ₹{udhaar_sales['total']:g}). "
                f"Cash collected: ₹{cash_collected:g}. Total customer debt: ₹{total_debt:g}."
            )

            return {
                "status": "success",
                "CashSalesTotal": cash_sales["total"],
                "CashSalesCount": cash_sales["count"],
                "UdhaarSalesTotal": udhaar_sales["total"],
                "UdhaarSalesCount": udhaar_sales["count"],
                "RepaymentsTotal": repayments["total"],
                "RepaymentsCount": repayments["count"],
                "RestockCostTotal": abs(restocks["total"]),
                "TotalRevenue": total_revenue,
                "CashCollected": cash_collected,
                "TotalOutstandingDebt": total_debt,
                "Message": message
            }
        finally:
            conn.close()

    def get_store_kpis(self):
        """
        Calculates comprehensive 2nd-degree retail analytics across:
        - Live inventory valuation & unit counts
        - Customer receivables & top debtors
        - Today's sales, udhaar, cash, and profit metrics
        - Top-selling products
        - Low stock warnings
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Inventory valuation
            cursor.execute('''
                SELECT 
                    count(*),
                    coalesce(sum(StockQuantity), 0),
                    coalesce(sum(StockQuantity * coalesce(SellingPrice, Price)), 0.0)
                FROM Inventory
            ''')
            inv_row = cursor.fetchone()
            total_skus = inv_row[0]
            total_units = inv_row[1]
            total_inv_value = float(inv_row[2])

            # 2. Customer receivables & top debtor
            cursor.execute('''
                SELECT count(*), coalesce(sum(OutstandingBalance), 0.0) FROM CustomerCredit
            ''')
            debt_row = cursor.fetchone()
            customer_count = debt_row[0]
            total_debt = float(debt_row[1])

            cursor.execute('''
                SELECT CustomerName, OutstandingBalance FROM CustomerCredit WHERE OutstandingBalance > 0 ORDER BY OutstandingBalance DESC LIMIT 1
            ''')
            top_debtor_row = cursor.fetchone()
            top_debtor = {
                "name": top_debtor_row[0],
                "balance": float(top_debtor_row[1])
            } if top_debtor_row else None

            # 3. Today's hisaab
            hisaab = self.get_today_hisaab()

            # 4. Top selling products today
            cursor.execute('''
                SELECT EntityName, coalesce(sum(Quantity), 0) as Qty, coalesce(sum(TotalAmount), 0.0) as Rev
                FROM Transactions
                WHERE TransactionType IN ('Sale', 'UdhaarSale') AND date(Timestamp) = date('now')
                GROUP BY EntityName
                ORDER BY Qty DESC
                LIMIT 5
            ''')
            top_products = [{"name": r[0], "quantity": r[1], "revenue": float(r[2])} for r in cursor.fetchall()]

            # 5. Low stock items
            low_stock = self.get_low_stock_items()

            return {
                "total_skus": total_skus,
                "total_units_in_stock": total_units,
                "total_inventory_valuation": total_inv_value,
                "customer_count": customer_count,
                "total_outstanding_debt": total_debt,
                "top_debtor": top_debtor,
                "today_hisaab": hisaab,
                "top_selling_products_today": top_products,
                "low_stock_count": low_stock["count"],
                "low_stock_items": [it["ItemName"] for it in low_stock["items"][:5]]
            }
        finally:
            conn.close()
