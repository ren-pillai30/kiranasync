import os
import sqlite3
from typing import Dict, List, Optional, Any
from backend.app.intent_parser import DB_PATH, ensure_transactions_schema, record_transaction

try:
    from thefuzz import process as fuzz_process
except ImportError:
    fuzz_process = None


class CallDBService:
    """
    Manages database reads and atomic updates for the Virtual Call Assistant.
    Adheres strictly to existing KiranaSync tables: Inventory, CustomerCredit, Transactions.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        ensure_transactions_schema(conn)
        return conn

    def get_store_context(self) -> Dict[str, Any]:
        """
        Fetches live inventory items and customer credit accounts for LLM reasoning prompt.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ItemID, ItemName, StockQuantity, Price FROM Inventory WHERE IsActive = 1"
            )
            inventory = [
                {
                    "ItemID": row["ItemID"],
                    "ItemName": row["ItemName"],
                    "StockQuantity": row["StockQuantity"],
                    "Price": float(row["Price"]),
                }
                for row in cursor.fetchall()
            ]

            cursor.execute(
                "SELECT CustomerID, CustomerName, OutstandingBalance FROM CustomerCredit WHERE IsActive = 1"
            )
            customers = [
                {
                    "CustomerID": row["CustomerID"],
                    "CustomerName": row["CustomerName"],
                    "OutstandingBalance": float(row["OutstandingBalance"] or 0.0),
                }
                for row in cursor.fetchall()
            ]

            return {
                "inventory": inventory,
                "customers": customers,
            }
        finally:
            conn.close()

    def match_inventory_item(
        self, candidate_name: str, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Matches a spoken or typed item name to an active item in Inventory.
        """
        clean_name = (candidate_name or "").strip().lower()
        if not clean_name:
            return None

        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ItemID, ItemName, StockQuantity, Price FROM Inventory WHERE IsActive = 1"
            )
            items = cursor.fetchall()
            if not items:
                return None

            # 1. Exact case-insensitive match
            for it in items:
                if it["ItemName"].lower() == clean_name:
                    return dict(it)

            # 2. Substring match
            for it in items:
                if clean_name in it["ItemName"].lower() or it["ItemName"].lower() in clean_name:
                    return dict(it)

            # 3. Fuzzy match if thefuzz is available
            if fuzz_process:
                name_map = {it["ItemName"]: dict(it) for it in items}
                best_match, score = fuzz_process.extractOne(candidate_name, list(name_map.keys()))
                if score >= 65:
                    return name_map[best_match]

            return None
        finally:
            if should_close:
                conn.close()

    def match_customer(
        self, candidate_name: str, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Matches a customer name to an active CustomerCredit record.
        """
        clean_name = (candidate_name or "").strip().lower()
        if not clean_name:
            return None

        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT CustomerID, CustomerName, OutstandingBalance FROM CustomerCredit WHERE IsActive = 1"
            )
            customers = cursor.fetchall()
            if not customers:
                return None

            for c in customers:
                if c["CustomerName"].lower() == clean_name:
                    return dict(c)

            for c in customers:
                if clean_name in c["CustomerName"].lower() or c["CustomerName"].lower() in clean_name:
                    return dict(c)

            if fuzz_process:
                name_map = {c["CustomerName"]: dict(c) for c in customers}
                best_match, score = fuzz_process.extractOne(candidate_name, list(name_map.keys()))
                if score >= 70:
                    return name_map[best_match]

            return None
        finally:
            if should_close:
                conn.close()

    def execute_order(
        self,
        items: List[Dict[str, Any]],
        customer_name: Optional[str] = None,
        payment_mode: str = "cash",
        raw_call_text: str = "",
    ) -> Dict[str, Any]:
        """
        Executes an order placed during a customer call.
        Decrements inventory and logs transactions.
        If payment_mode is 'udhaar', logs credit balance for the customer.
        """
        if not items:
            return {"status": "error", "message": "No order items specified."}

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            resolved_order_items = []
            total_order_amount = 0.0

            # 1. Validate all items and stock using the active connection
            for entry in items:
                req_name = str(entry.get("name") or entry.get("entity") or "").strip()
                try:
                    qty = int(entry.get("quantity", 1))
                except (ValueError, TypeError):
                    qty = 1

                if qty <= 0:
                    continue

                matched = self.match_inventory_item(req_name, conn=conn)
                if not matched:
                    return {
                        "status": "error",
                        "message": f"Item '{req_name}' was not found in active inventory.",
                    }

                available_stock = int(matched["StockQuantity"])
                if available_stock < qty:
                    return {
                        "status": "error",
                        "message": f"Insufficient stock for {matched['ItemName']}. Only {available_stock} available.",
                    }

                item_total = float(matched["Price"]) * qty
                total_order_amount += item_total
                resolved_order_items.append({
                    "item_id": matched["ItemID"],
                    "item_name": matched["ItemName"],
                    "quantity": qty,
                    "unit_price": float(matched["Price"]),
                    "item_total": item_total,
                    "new_stock": available_stock - qty,
                })

            if not resolved_order_items:
                return {"status": "error", "message": "No valid order items to process."}

            # 2. Deduct inventory and record sale transactions
            for it in resolved_order_items:
                cursor.execute(
                    "UPDATE Inventory SET StockQuantity = ? WHERE ItemID = ?",
                    (it["new_stock"], it["item_id"]),
                )
                cmd_note = raw_call_text or f"Call Order: {it['quantity']}x {it['item_name']}"
                record_transaction(
                    cursor,
                    cmd_note,
                    it["item_total"],
                    "Sale",
                    it["item_name"],
                    it["quantity"],
                )

            # 3. Handle udhaar (credit) if payment is on credit
            is_credit = str(payment_mode).lower() in ("udhaar", "credit")
            new_customer_balance = None
            cust_name_clean = (customer_name or "").strip()

            if is_credit and cust_name_clean:
                matched_cust = self.match_customer(cust_name_clean, conn=conn)
                if matched_cust:
                    cust_id = matched_cust["CustomerID"]
                    cust_actual_name = matched_cust["CustomerName"]
                    new_customer_balance = float(matched_cust["OutstandingBalance"]) + total_order_amount
                    cursor.execute(
                        "UPDATE CustomerCredit SET OutstandingBalance = ? WHERE CustomerID = ?",
                        (new_customer_balance, cust_id),
                    )
                else:
                    cust_actual_name = cust_name_clean
                    new_customer_balance = total_order_amount
                    cursor.execute(
                        "INSERT INTO CustomerCredit (CustomerName, OutstandingBalance, IsActive) VALUES (?, ?, 1)",
                        (cust_actual_name, new_customer_balance),
                    )

                record_transaction(
                    cursor,
                    raw_call_text or f"Call Order Udhaar: Rs {total_order_amount:g} for {cust_actual_name}",
                    total_order_amount,
                    "Credit",
                    cust_actual_name,
                )

            conn.commit()

            return {
                "status": "success",
                "action": "order_placed",
                "items": resolved_order_items,
                "total_amount": total_order_amount,
                "payment_mode": "udhaar" if is_credit else "cash",
                "customer_name": cust_name_clean if is_credit else None,
                "new_balance": new_customer_balance,
                "message": (
                    f"Order placed successfully for Rs {total_order_amount:g} "
                    f"({len(resolved_order_items)} item(s))."
                    + (f" Logged to {cust_name_clean}'s udhaar." if is_credit and cust_name_clean else "")
                ),
            }
        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": f"Database order failure: {str(e)}"}
        finally:
            conn.close()

    def execute_credit_log(
        self,
        customer_name: str,
        amount: float,
        raw_call_text: str = "",
    ) -> Dict[str, Any]:
        """
        Logs customer udhaar (debt) into CustomerCredit and Transactions.
        """
        cust_name = (customer_name or "").strip()
        if not cust_name:
            return {"status": "error", "message": "Customer name is required to log udhaar."}

        try:
            credit_amount = float(amount)
            if credit_amount <= 0:
                return {"status": "error", "message": "Credit amount must be greater than zero."}
        except (ValueError, TypeError):
            return {"status": "error", "message": "Invalid credit amount."}

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            matched_cust = self.match_customer(cust_name, conn=conn)

            if matched_cust:
                cust_id = matched_cust["CustomerID"]
                actual_name = matched_cust["CustomerName"]
                new_balance = float(matched_cust["OutstandingBalance"]) + credit_amount
                cursor.execute(
                    "UPDATE CustomerCredit SET OutstandingBalance = ? WHERE CustomerID = ?",
                    (new_balance, cust_id),
                )
            else:
                actual_name = cust_name
                new_balance = credit_amount
                cursor.execute(
                    "INSERT INTO CustomerCredit (CustomerName, OutstandingBalance, IsActive) VALUES (?, ?, 1)",
                    (actual_name, new_balance),
                )

            record_transaction(
                cursor,
                raw_call_text or f"Call Udhaar Log: Rs {credit_amount:g} for {actual_name}",
                credit_amount,
                "Credit",
                actual_name,
            )
            conn.commit()

            return {
                "status": "success",
                "action": "udhaar_logged",
                "customer_name": actual_name,
                "amount": credit_amount,
                "new_balance": new_balance,
                "message": f"Logged Rs {credit_amount:g} udhaar for {actual_name}. New balance: Rs {new_balance:g}.",
            }
        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": f"Database credit failure: {str(e)}"}
        finally:
            conn.close()

    def execute_repayment(
        self,
        customer_name: str,
        amount: float,
        raw_call_text: str = "",
    ) -> Dict[str, Any]:
        """
        Records a repayment made by a customer to reduce outstanding udhaar.
        """
        cust_name = (customer_name or "").strip()
        if not cust_name:
            return {"status": "error", "message": "Customer name is required for repayment."}

        try:
            repay_amount = float(amount)
            if repay_amount <= 0:
                return {"status": "error", "message": "Repayment amount must be positive."}
        except (ValueError, TypeError):
            return {"status": "error", "message": "Invalid repayment amount."}

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            matched_cust = self.match_customer(cust_name, conn=conn)
            if not matched_cust:
                return {"status": "error", "message": f"Customer '{cust_name}' was not found in records."}

            cust_id = matched_cust["CustomerID"]
            actual_name = matched_cust["CustomerName"]
            curr_balance = float(matched_cust["OutstandingBalance"])
            new_balance = max(0.0, curr_balance - repay_amount)

            cursor.execute(
                "UPDATE CustomerCredit SET OutstandingBalance = ? WHERE CustomerID = ?",
                (new_balance, cust_id),
            )

            record_transaction(
                cursor,
                raw_call_text or f"Call Repayment: Rs {repay_amount:g} by {actual_name}",
                -repay_amount,
                "Repayment",
                actual_name,
            )
            conn.commit()

            return {
                "status": "success",
                "action": "repayment_recorded",
                "customer_name": actual_name,
                "amount": repay_amount,
                "new_balance": new_balance,
                "message": f"Recorded Rs {repay_amount:g} repayment from {actual_name}. Remaining balance: Rs {new_balance:g}.",
            }
        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": f"Database repayment failure: {str(e)}"}
        finally:
            conn.close()

    def execute_action(
        self,
        action_type: str,
        action_data: Optional[Dict[str, Any]] = None,
        raw_call_text: str = "",
    ) -> Dict[str, Any]:
        """
        Dispatches structured action generated by the Gemini reasoning pipeline.
        """
        data = action_data or {}
        action = (action_type or "").lower().strip()

        if action == "order":
            items = data.get("items", [])
            cust_name = data.get("customer_name")
            mode = data.get("payment_mode", "cash")
            return self.execute_order(items, customer_name=cust_name, payment_mode=mode, raw_call_text=raw_call_text)

        elif action == "credit_log":
            cust_name = data.get("customer_name")
            amount = data.get("amount", 0.0)
            return self.execute_credit_log(customer_name=cust_name, amount=amount, raw_call_text=raw_call_text)

        elif action == "repayment":
            cust_name = data.get("customer_name")
            amount = data.get("amount", 0.0)
            return self.execute_repayment(customer_name=cust_name, amount=amount, raw_call_text=raw_call_text)

        elif action == "inquiry":
            return {"status": "success", "action": "inquiry_answered"}

        return {"status": "noop", "action": "general_chitchat"}

