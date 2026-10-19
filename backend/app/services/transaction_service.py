import sqlite3
from backend.app.intent_parser import ensure_transactions_schema, record_transaction

class TransactionService:
    @staticmethod
    def commit_sale(conn, payload, command_id):
        """
        Atomically decrements inventory stock and creates a Sale transaction.
        Re-validates stock at confirmation time to prevent stale-state race conditions.
        """
        cursor = conn.cursor()
        ensure_transactions_schema(conn)

        item_id = payload.get("ItemID")
        quantity = int(payload.get("Quantity", 0))
        raw_command = payload.get("RawCommand", "")

        if not item_id or quantity <= 0:
            raise ValueError("Valid ItemID and positive quantity are required.")

        cursor.execute("SELECT ItemName, StockQuantity, Price FROM Inventory WHERE ItemID = ?", (item_id,))
        item = cursor.fetchone()
        if not item:
            raise ValueError("Inventory item no longer exists.")

        item_name, current_stock, price = item[0], int(item[1]), float(item[2])
        if current_stock < quantity:
            raise ValueError(f"Insufficient stock for {item_name}. Only {current_stock} left (requested {quantity}).")

        new_stock = current_stock - quantity
        total_amount = price * quantity

        cursor.execute("UPDATE Inventory SET StockQuantity = ? WHERE ItemID = ?", (new_stock, item_id))
        record_transaction(cursor, raw_command or f"Sale {quantity} {item_name}", total_amount, "Sale", item_name, quantity)
        txn_id = cursor.lastrowid

        return {
            "TxnID": txn_id,
            "Action": "inventory_updated",
            "Message": f"Sold {quantity} {item_name}. Stock left: {new_stock}.",
            "ItemName": item_name,
            "Quantity": quantity,
            "NewStock": new_stock,
            "TotalAmount": total_amount
        }

    @staticmethod
    def commit_restock(conn, payload, command_id):
        """
        Atomically increases inventory stock and creates a Restock transaction.
        Supports single item restock or multiple newly confirmed MRP items.
        """
        cursor = conn.cursor()
        ensure_transactions_schema(conn)

        raw_command = payload.get("RawCommand", "")
        item_id = payload.get("ItemID")
        items = payload.get("Items", []) # For multiple MRP confirmation

        if items:
            base_item_name = payload.get("ItemName", "").strip()
            if not base_item_name:
                raise ValueError("ItemName is required.")
            
            added_records = []
            total_restock_cost = 0.0
            
            for item in items:
                price = float(item["Price"])
                quantity = int(item["Quantity"])
                if quantity <= 0 or price <= 0:
                    continue
                variant_name = f"{base_item_name} (MRP ₹{price:g})"
                cursor.execute("SELECT ItemID, StockQuantity FROM Inventory WHERE ItemName = ?", (variant_name,))
                existing = cursor.fetchone()
                if existing:
                    new_stock = int(existing[1]) + quantity
                    cursor.execute("UPDATE Inventory SET StockQuantity = ?, Price = ? WHERE ItemID = ?", (new_stock, price, existing[0]))
                else:
                    new_stock = quantity
                    cursor.execute("INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)", (variant_name, quantity, price))
                
                cost = price * quantity
                total_restock_cost += cost
                added_records.append({"ItemName": variant_name, "Quantity": quantity, "NewStock": new_stock, "Price": price})

            record_transaction(cursor, raw_command or f"Restock {base_item_name}", -total_restock_cost, "Restock", base_item_name)
            txn_id = cursor.lastrowid

            return {
                "TxnID": txn_id,
                "Action": "inventory_restocked",
                "Message": f"Restocked {len(added_records)} variant(s) of {base_item_name}.",
                "Variants": added_records,
                "TotalCost": total_restock_cost
            }
        elif item_id:
            quantity = int(payload.get("Quantity", 0))
            if quantity <= 0:
                raise ValueError("Positive quantity is required for restock.")
            
            cursor.execute("SELECT ItemName, StockQuantity, Price FROM Inventory WHERE ItemID = ?", (item_id,))
            item = cursor.fetchone()
            if not item:
                raise ValueError("Inventory item no longer exists.")
            
            item_name, current_stock, price = item[0], int(item[1]), float(item[2])
            new_stock = current_stock + quantity
            total_cost = price * quantity

            cursor.execute("UPDATE Inventory SET StockQuantity = ? WHERE ItemID = ?", (new_stock, item_id))
            record_transaction(cursor, raw_command or f"Restock {quantity} {item_name}", -total_cost, "Restock", item_name, quantity)
            txn_id = cursor.lastrowid

            return {
                "TxnID": txn_id,
                "Action": "inventory_restocked",
                "Message": f"Restocked {quantity} {item_name}. Total stock: {new_stock}.",
                "ItemName": item_name,
                "Quantity": quantity,
                "NewStock": new_stock,
                "TotalCost": total_cost
            }
        else:
            raise ValueError("Restock payload must include ItemID or Items list.")

    @staticmethod
    def commit_credit(conn, payload, command_id):
        """
        Atomically increments customer debt and records a Credit transaction.
        """
        cursor = conn.cursor()
        ensure_transactions_schema(conn)

        customer_name = payload.get("CustomerName", "").strip()
        amount = float(payload.get("Amount", 0))
        raw_command = payload.get("RawCommand", "")

        if not customer_name or amount <= 0:
            raise ValueError("Valid CustomerName and positive Amount are required.")

        cursor.execute("SELECT CustomerID, OutstandingBalance FROM CustomerCredit WHERE CustomerName = ?", (customer_name,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES (?, ?)", (customer_name, amount))
            customer_id = cursor.lastrowid
            new_balance = amount
            message = f"Created new account for {customer_name} with Rs {amount:g} balance."
        else:
            customer_id, current_bal = row[0], float(row[1])
            new_balance = current_bal + amount
            cursor.execute("UPDATE CustomerCredit SET OutstandingBalance = ? WHERE CustomerID = ?", (new_balance, customer_id))
            message = f"Added Rs {amount:g} to {customer_name}. New Balance: Rs {new_balance:g}."

        record_transaction(cursor, raw_command or f"Credit Rs {amount:g} {customer_name}", amount, "Credit", customer_name)
        txn_id = cursor.lastrowid

        return {
            "TxnID": txn_id,
            "Action": "udhaar_added",
            "Message": message,
            "CustomerName": customer_name,
            "Amount": amount,
            "NewBalance": new_balance
        }

    @staticmethod
    def commit_udhaar_sale(conn, payload, command_id):
        """
        Atomically decrements inventory stock, increases customer debt,
        and creates an UdhaarSale transaction.
        """
        cursor = conn.cursor()
        ensure_transactions_schema(conn)

        item_id = payload.get("ItemID")
        quantity = int(payload.get("Quantity", 0))
        customer_name = payload.get("CustomerName", "").strip()
        raw_command = payload.get("RawCommand", "")

        if not item_id or quantity <= 0 or not customer_name:
            raise ValueError("ItemID, positive Quantity, and CustomerName are required for UdhaarSale.")

        # 1. Validate inventory
        cursor.execute("SELECT ItemName, StockQuantity, coalesce(SellingPrice, Price) FROM Inventory WHERE ItemID = ?", (item_id,))
        item = cursor.fetchone()
        if not item:
            raise ValueError("Inventory item no longer exists.")
        item_name, current_stock, unit_price = item[0], int(item[1]), float(item[2])
        if current_stock < quantity:
            raise ValueError(f"Insufficient stock for {item_name}. Only {current_stock} left.")

        # 2. Validate/find customer
        cursor.execute("SELECT CustomerID, OutstandingBalance FROM CustomerCredit WHERE CustomerName = ?", (customer_name,))
        cust_row = cursor.fetchone()
        sale_amount = unit_price * quantity

        if not cust_row:
            cursor.execute("INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES (?, ?)", (customer_name, sale_amount))
            customer_id = cursor.lastrowid
            new_balance = sale_amount
        else:
            customer_id, current_bal = cust_row[0], float(cust_row[1])
            new_balance = current_bal + sale_amount
            cursor.execute("UPDATE CustomerCredit SET OutstandingBalance = ? WHERE CustomerID = ?", (new_balance, customer_id))

        # 3. Deduct stock
        new_stock = current_stock - quantity
        cursor.execute("UPDATE Inventory SET StockQuantity = ? WHERE ItemID = ?", (new_stock, item_id))

        # 4. Insert transaction
        record_transaction(
            cursor,
            raw_command or f"Udhaar Sale {quantity} {item_name} to {customer_name}",
            sale_amount,
            "UdhaarSale",
            f"{item_name} ({customer_name})",
            quantity
        )
        txn_id = cursor.lastrowid

        return {
            "TxnID": txn_id,
            "Action": "udhaar_sale_completed",
            "Message": f"Sold {quantity} {item_name} on credit to {customer_name}. Total: ₹{sale_amount:g}. New debt: ₹{new_balance:g}.",
            "ItemName": item_name,
            "CustomerName": customer_name,
            "Quantity": quantity,
            "NewStock": new_stock,
            "NewBalance": new_balance,
            "TotalAmount": sale_amount
        }

    @staticmethod
    def commit_repayment(conn, payload, command_id):
        """
        Atomically reduces customer debt and records a Repayment transaction.
        Guarantees:
        - Never silently increases debt.
        - Rejects or stops overpayment unless explicitly approved.
        """
        cursor = conn.cursor()
        ensure_transactions_schema(conn)

        customer_name = payload.get("CustomerName", "").strip()
        amount = float(payload.get("Amount", 0))
        allow_overpayment = bool(payload.get("AllowOverpayment", False))
        raw_command = payload.get("RawCommand", "")

        if not customer_name or amount <= 0:
            raise ValueError("CustomerName and positive repayment Amount are required.")

        cursor.execute("SELECT CustomerID, OutstandingBalance FROM CustomerCredit WHERE CustomerName = ?", (customer_name,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Customer '{customer_name}' does not exist.")

        customer_id, current_bal = row[0], float(row[1])
        if amount > current_bal and not allow_overpayment:
            raise ValueError(
                f"Payment of ₹{amount:g} exceeds {customer_name}'s balance of ₹{current_bal:g}. "
                f"Requires explicit overpayment confirmation."
            )

        new_balance = max(0.0, current_bal - amount)
        cursor.execute("UPDATE CustomerCredit SET OutstandingBalance = ? WHERE CustomerID = ?", (new_balance, customer_id))

        record_transaction(
            cursor,
            raw_command or f"Repayment from {customer_name}",
            amount,
            "Repayment",
            customer_name
        )
        txn_id = cursor.lastrowid

        return {
            "TxnID": txn_id,
            "Action": "repayment_recorded",
            "Message": f"Recorded payment of ₹{amount:g} from {customer_name}. Remaining balance: ₹{new_balance:g}.",
            "CustomerName": customer_name,
            "AmountPaid": amount,
            "NewBalance": new_balance
        }
