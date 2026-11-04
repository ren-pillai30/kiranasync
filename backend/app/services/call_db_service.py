import os
import sqlite3
import difflib
import re
import unicodedata
from typing import Dict, List, Optional, Any
from backend.app.intent_parser import DB_PATH, ensure_transactions_schema, record_transaction
from backend.app.measurement_utils import (
    extract_measurement,
    strip_measurement,
    analyze_measurement_matches,
    are_measurements_equal,
)

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

    @staticmethod
    def _column_names(cursor: sqlite3.Cursor, table: str) -> set:
        cursor.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}

    @staticmethod
    def _normalize_name(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value or "").casefold()
        normalized = re.sub(r"\(.*?\)|\[.*?\]", " ", normalized)
        normalized = re.sub(r"(?:\b(?:mrp|price)\b\s*[₹rs.]?\s*)?\d+(?:\.\d+)?\s*(?:kg|g|gm|gram|grams|ml|l|litre|liters|pcs?|pack|packet)?", " ", normalized)
        return " ".join(re.findall(r"\w+", normalized, flags=re.UNICODE))

    def get_store_context(self) -> Dict[str, Any]:
        """
        Fetches live inventory items and customer credit accounts for LLM reasoning prompt.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            inventory_columns = self._column_names(cursor, "Inventory")
            hindi_inventory_column = "ItemNameHindi" if "ItemNameHindi" in inventory_columns else None
            inventory_query = (
                "SELECT ItemID, ItemName, StockQuantity, Price"
                + (", ItemNameHindi" if hindi_inventory_column else "")
                + " FROM Inventory WHERE IsActive = 1"
            )
            cursor.execute(inventory_query)
            inventory = [
                {
                    "ItemID": row["ItemID"],
                    "ItemName": row["ItemName"],
                    "ItemNameHindi": row["ItemNameHindi"] if hindi_inventory_column else "",
                    "StockQuantity": row["StockQuantity"],
                    "Price": float(row["Price"]),
                }
                for row in cursor.fetchall()
            ]

            customer_columns = self._column_names(cursor, "CustomerCredit")
            customer_hindi_column = "CustomerNameHindi" if "CustomerNameHindi" in customer_columns else None
            customer_query = (
                "SELECT CustomerID, CustomerName, OutstandingBalance"
                + (", CustomerNameHindi" if customer_hindi_column else "")
                + " FROM CustomerCredit WHERE IsActive = 1"
            )
            cursor.execute(customer_query)
            customers = [
                {
                    "CustomerID": row["CustomerID"],
                    "CustomerName": row["CustomerName"],
                    "CustomerNameHindi": row["CustomerNameHindi"] if customer_hindi_column else "",
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

    @classmethod
    def answer_inventory_inquiry(
        cls,
        utterance: str,
        inventory: List[Dict[str, Any]],
        language_code: str = "hi-IN",
    ) -> Optional[str]:
        """Answer a clear stock/price lookup from live inventory if Gemini is unavailable."""
        normalized_utterance = unicodedata.normalize("NFKC", utterance or "").casefold()
        stock_terms = {
            "stock", "available", "availability", "inventory", "have",
            "स्टॉक", "उपलब्ध", "कितना", "कितनी", "कितने",
        }
        price_terms = {
            "price", "cost", "rate", "mrp", "daam", "keemat",
            "दाम", "कीमत", "भाव", "मूल्य",
        }
        if not any(term in normalized_utterance for term in stock_terms | price_terms):
            return None

        stop_words = {
            "a", "an", "the", "is", "it", "do", "does", "you", "have", "what",
            "how", "much", "many", "stock", "available", "availability", "inventory",
            "and", "price", "cost", "rate", "mrp", "tell", "me", "please", "of",
            "hai", "hain", "kya", "ka", "ki", "ke", "kitna", "kitni", "kitne",
            "aur", "bataye", "batao", "daam", "keemat", "par", "mein",
            "है", "हैं", "क्या", "का", "की", "के", "कितना", "कितनी", "कितने",
            "और", "दाम", "कीमत", "बताओ", "बताइए", "में", "पर", "मिलेगा",
            "मिलेगी", "मिलता", "मिलती", "उपलब्ध", "स्टॉक", "की",
        }
        query_tokens = {
            token
            for token in re.findall(r"\w+", normalized_utterance, flags=re.UNICODE)
            if token not in stop_words and not token.isdigit()
        }
        if not query_tokens:
            return None

        matches = []
        for item in inventory:
            aliases = [
                str(item.get("ItemName") or ""),
                str(item.get("ItemNameHindi") or ""),
            ]
            alias_tokens = {
                token
                for alias in aliases
                for token in re.findall(
                    r"\w+",
                    unicodedata.normalize("NFKC", alias).casefold(),
                    flags=re.UNICODE,
                )
                if token not in stop_words and not token.isdigit()
            }
            if not alias_tokens:
                continue
            exact = query_tokens & alias_tokens
            fuzzy_hits = {
                query_token
                for query_token in query_tokens - exact
                if max(
                    (
                        difflib.SequenceMatcher(None, query_token, alias_token).ratio()
                        for alias_token in alias_tokens
                    ),
                    default=0,
                ) >= 0.82
            }
            matched_tokens = exact | fuzzy_hits
            if matched_tokens:
                matches.append((len(matched_tokens) / len(query_tokens), len(exact), item))

        if not matches:
            return None
        best_score = max((score, exact_count) for score, exact_count, _ in matches)
        best_items = [
            item
            for score, exact_count, item in matches
            if (score, exact_count) == best_score
        ]
        if best_score[0] < 0.5 or best_score[1] == 0:
            return None

        asks_stock = any(term in normalized_utterance for term in stock_terms)
        asks_price = any(term in normalized_utterance for term in price_terms)
        details = []
        for item in best_items:
            if language_code == "hi-IN":
                name = item.get("ItemNameHindi") or item.get("ItemName") or "वस्तु"
            else:
                name = item.get("ItemName") or item.get("ItemNameHindi") or "Item"
            stock = item.get("StockQuantity") or 0
            price = f"₹{float(item.get('Price') or 0):g}"
            if language_code == "hi-IN":
                stock_text = (
                    f"स्टॉक {stock}" if stock else "उपलब्ध नहीं है"
                )
                if asks_stock and asks_price:
                    details.append(f"{name} का {stock_text} है और कीमत {price} है")
                elif asks_stock:
                    details.append(f"{name} का {stock_text} है")
                else:
                    details.append(f"{name} की कीमत {price} है")
                continue

            facts = []
            if asks_stock:
                facts.append(f"stock {stock}" if stock else "out of stock")
            if asks_price:
                facts.append(f"price {price}")
            details.append(f"{name}: {', '.join(facts)}")
        if language_code == "hi-IN":
            return "Gemini अभी उपलब्ध नहीं है। " + "। ".join(details) + "।"
        return "Gemini is temporarily unavailable. " + "; ".join(details) + "."

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

        req_meas = extract_measurement(candidate_name)

        def is_measurement_compatible(it_row):
            if not req_meas:
                return True
            it_meas = extract_measurement(it_row["ItemName"])
            if not it_meas:
                return True
            return are_measurements_equal(req_meas, it_meas)

        try:
            cursor = conn.cursor()
            inventory_columns = self._column_names(cursor, "Inventory")
            has_hindi = "ItemNameHindi" in inventory_columns
            query = (
                "SELECT ItemID, ItemName, StockQuantity, Price"
                + (", ItemNameHindi" if has_hindi else "")
                + " FROM Inventory WHERE IsActive = 1"
            )
            cursor.execute(query)
            items = cursor.fetchall()
            if not items:
                return None

            candidate_normalized = self._normalize_name(candidate_name)

            def names_for(item):
                names = [item["ItemName"]]
                if has_hindi and item["ItemNameHindi"]:
                    names.append(item["ItemNameHindi"])
                return names

            # 1. Exact or normalized match, including the stored Hindi name.
            for it in items:
                for stored_name in names_for(it):
                    if stored_name.lower() == clean_name or self._normalize_name(stored_name) == candidate_normalized:
                        if is_measurement_compatible(it):
                            return dict(it)

            # 2. Gemini entity matching: resolves speech across scripts, transliterations, and variant names.
            from backend.app.gemini_understanding import resolve_catalog_entity

            catalog_to_item = {}
            for it in items:
                for stored_name in names_for(it):
                    catalog_to_item[stored_name] = dict(it)
            gemini_match = resolve_catalog_entity(
                candidate_name,
                list(catalog_to_item.keys()),
                "product",
                {"spoken_name": candidate_name},
            )
            if gemini_match:
                catalog_fold = {k.casefold(): v for k, v in catalog_to_item.items()}
                if gemini_match.casefold() in catalog_fold:
                    resolved_item = catalog_fold[gemini_match.casefold()]
                    if is_measurement_compatible(resolved_item):
                        return resolved_item

            # 2. Substring match
            for it in items:
                if is_measurement_compatible(it) and (
                    clean_name in it["ItemName"].lower()
                    or it["ItemName"].lower() in clean_name
                    or (has_hindi and it["ItemNameHindi"] and clean_name in it["ItemNameHindi"].lower())
                ):
                    return dict(it)

            # 3. Fuzzy match if thefuzz is available
            if fuzz_process:
                compatible_items = [it for it in items if is_measurement_compatible(it)]
                if compatible_items:
                    name_map = {}
                    for it in compatible_items:
                        for stored_name in names_for(it):
                            name_map[stored_name] = dict(it)
                    best_match, score = fuzz_process.extractOne(candidate_normalized, [self._normalize_name(name) for name in name_map])
                    if score >= 65:
                        return next((item for name, item in name_map.items() if self._normalize_name(name) == best_match))

            return None
        finally:
            if should_close:
                conn.close()

    def check_inventory_measurement_mismatch(
        self, candidate_name: str, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Checks if candidate_name mentions a measurement that doesn't exist in inventory,
        but other sizes/measurements for that product DO exist.
        """
        req_meas = extract_measurement(candidate_name)
        if not req_meas:
            return None

        base_name = strip_measurement(candidate_name).strip().lower()
        if not base_name:
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
            matching_variants = []
            for it in items:
                it_name = it["ItemName"].lower()
                if base_name in it_name or difflib.SequenceMatcher(None, base_name, it_name).ratio() >= 0.7:
                    matching_variants.append(it["ItemName"])

            if not matching_variants:
                return None

            analysis = analyze_measurement_matches(candidate_name, matching_variants)
            if analysis["status"] == "measurement_mismatch":
                return {
                    "requested_measurement": analysis["requested_measurement"],
                    "other_measurements": analysis["other_measurements"],
                    "matching_items": matching_variants,
                }
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

            # Gemini customer matching across scripts and transliterations
            from backend.app.gemini_understanding import resolve_catalog_entity
            cust_catalog = {c["CustomerName"]: dict(c) for c in customers}
            gemini_match = resolve_catalog_entity(
                candidate_name,
                list(cust_catalog.keys()),
                "customer",
                {"spoken_name": candidate_name},
            )
            if gemini_match:
                cust_fold = {k.casefold(): v for k, v in cust_catalog.items()}
                if gemini_match.casefold() in cust_fold:
                    return cust_fold[gemini_match.casefold()]

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
                    mismatch = self.check_inventory_measurement_mismatch(req_name, conn=conn)
                    if mismatch:
                        return {
                            "status": "measurement_mismatch",
                            "action": "measurement_mismatch",
                            "message": f"Exact measurement ({mismatch['requested_measurement']}) is not available in stock. Other sizes in stock: {', '.join(mismatch['other_measurements'])}.",
                            "requested_measurement": mismatch["requested_measurement"],
                            "other_measurements": mismatch["other_measurements"],
                        }
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
