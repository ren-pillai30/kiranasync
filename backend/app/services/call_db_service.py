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
from backend.app.database import is_postgres_database

class CallDBService:
    """
    Manages database reads and atomic updates for the Virtual Call Assistant.
    Adheres strictly to existing KiranaSync tables: Inventory, CustomerCredit, Transactions.
    """

    def __init__(self, db_path: Optional[str] = None, store_id: Optional[int] = None):
        self.db_path = db_path or DB_PATH
        self.store_id = store_id
        self.use_postgres = db_path is None and is_postgres_database()

    def _active_store_id(self) -> int:
        if self.store_id is not None:
            return self.store_id
        from flask_login import current_user
        return getattr(current_user, "store_id", 1)

    def _postgres_inventory(self) -> List[Dict[str, Any]]:
        from backend.app.models import StoreInventory

        return [{
            "ItemID": item.item_id,
            "ItemName": item.item_name,
            "ItemNameHindi": item.item_name_hindi,
            "StockQuantity": item.stock_quantity,
            "Price": float(item.price or 0),
        } for item in StoreInventory.query.filter_by(
            store_id=self._active_store_id(),
            is_active=True,
        ).order_by(StoreInventory.item_id).all()]

    def _postgres_customers(self) -> List[Dict[str, Any]]:
        from backend.app.models import StoreCredit

        return [{
            "CustomerID": customer.customer_id,
            "CustomerName": customer.customer_name,
            "CustomerNameHindi": customer.customer_name_hindi,
            "OutstandingBalance": float(customer.outstanding_balance or 0),
        } for customer in StoreCredit.query.filter_by(
            store_id=self._active_store_id(),
            is_active=True,
        ).order_by(StoreCredit.customer_id).all()]

    def _record_postgres_transaction(
        self,
        command_text: str,
        amount: float,
        transaction_type: str,
        entity_name: str,
        quantity: Optional[int] = None,
    ) -> None:
        from backend.app.database import db
        from backend.app.models import StoreTransaction

        store_id = self._active_store_id()
        max_txn_id = db.session.query(db.func.max(StoreTransaction.txn_id)).filter_by(
            store_id=store_id
        ).scalar() or 0
        db.session.add(StoreTransaction(
            store_id=store_id,
            txn_id=max_txn_id + 1,
            command_text=command_text[:1000],
            total_amount=amount,
            transaction_type=transaction_type,
            entity_name=entity_name,
            quantity=quantity,
        ))

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
        if self.use_postgres:
            return {
                "inventory": self._postgres_inventory(),
                "customers": self._postgres_customers(),
            }

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
        self,
        candidate_name: str,
        conn: Optional[sqlite3.Connection] = None,
        raw_transcript: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Matches a spoken or typed item name to an active item in Inventory.
        """
        clean_name = (candidate_name or "").strip().lower()
        if not clean_name:
            return None

        if self.use_postgres and conn is None:
            return self._match_postgres_inventory(candidate_name, raw_transcript)

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

            # Prefer exact names; normalized matches can collapse distinct package variants.
            for it in items:
                for stored_name in names_for(it):
                    if stored_name.casefold() == clean_name.casefold():
                        if is_measurement_compatible(it):
                            return dict(it)

            name_matches = {
                it["ItemID"]: dict(it)
                for it in items
                if is_measurement_compatible(it)
                and any(
                    self._normalize_name(stored_name) == candidate_normalized
                    or clean_name in stored_name.casefold()
                    or stored_name.casefold() in clean_name
                    for stored_name in names_for(it)
                )
            }
            if len(name_matches) == 1:
                return next(iter(name_matches.values()))

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
                {
                    "spoken_name": candidate_name,
                    "raw_transcript": raw_transcript or candidate_name,
                },
            )
            if gemini_match:
                catalog_fold = {k.casefold(): v for k, v in catalog_to_item.items()}
                if gemini_match.casefold() in catalog_fold:
                    resolved_item = catalog_fold[gemini_match.casefold()]
                    if is_measurement_compatible(resolved_item):
                        return resolved_item

            return None
        finally:
            if should_close:
                conn.close()

    def _match_postgres_inventory(
        self, candidate_name: str, raw_transcript: str = ""
    ) -> Optional[Dict[str, Any]]:
        items = self._postgres_inventory()
        clean_name = candidate_name.strip().casefold()
        candidate_normalized = self._normalize_name(candidate_name)
        req_meas = extract_measurement(candidate_name)

        def compatible(item):
            item_measurement = extract_measurement(item["ItemName"])
            return (
                not req_meas
                or not item_measurement
                or are_measurements_equal(req_meas, item_measurement)
            )

        def aliases_for(item):
            return [
                alias for alias in (item["ItemName"], item.get("ItemNameHindi"))
                if alias
            ]

        for item in items:
            if any(alias.casefold() == clean_name for alias in aliases_for(item)) and compatible(item):
                return item

        matches = [
            item for item in items
            if compatible(item) and any(
                self._normalize_name(alias) == candidate_normalized
                or clean_name in alias.casefold()
                or alias.casefold() in clean_name
                for alias in aliases_for(item)
            )
        ]
        if len(matches) == 1:
            return matches[0]

        from backend.app.gemini_understanding import resolve_catalog_entity

        catalog_items = {}
        for item in items:
            for alias in aliases_for(item):
                catalog_items[alias] = item
        resolved = resolve_catalog_entity(
            candidate_name,
            list(catalog_items),
            "product",
            {
                "spoken_name": candidate_name,
                "raw_transcript": raw_transcript or candidate_name,
            },
        )
        if resolved:
            item = next(
                (
                    value for alias, value in catalog_items.items()
                    if alias.casefold() == resolved.casefold()
                ),
                None,
            )
            if item and compatible(item):
                return item
        return None

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
        self,
        candidate_name: str,
        conn: Optional[sqlite3.Connection] = None,
        raw_transcript: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Matches a customer name to an active CustomerCredit record.
        """
        clean_name = (candidate_name or "").strip().lower()
        if not clean_name:
            return None

        if self.use_postgres and conn is None:
            return self._match_postgres_customer(candidate_name, raw_transcript)

        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()
            customer_columns = self._column_names(cursor, "CustomerCredit")
            has_hindi_name = "CustomerNameHindi" in customer_columns
            cursor.execute(
                "SELECT CustomerID, CustomerName, OutstandingBalance"
                + (", CustomerNameHindi" if has_hindi_name else "")
                + " FROM CustomerCredit WHERE IsActive = 1"
            )
            customers = cursor.fetchall()
            if not customers:
                return None

            alias_candidates = {}
            alias_values = {}
            for c in customers:
                aliases = [c["CustomerName"]]
                if has_hindi_name and c["CustomerNameHindi"]:
                    aliases.append(c["CustomerNameHindi"].strip())
                for alias in aliases:
                    if alias:
                        key = alias.casefold()
                        alias_candidates.setdefault(key, {})[c["CustomerID"]] = dict(c)
                        alias_values.setdefault(key, alias)

            customer_aliases = {
                key: next(iter(records.values()))
                for key, records in alias_candidates.items()
                if len(records) == 1
            }
            customer_catalog = [
                alias_values[key]
                for key in customer_aliases
            ]

            if clean_name.casefold() in customer_aliases:
                return customer_aliases[clean_name.casefold()]

            # Gemini resolves transliterations and pronunciations to one supplied customer name.
            from backend.app.gemini_understanding import resolve_catalog_entity
            gemini_match = resolve_catalog_entity(
                candidate_name,
                customer_catalog,
                "customer",
                {
                    "spoken_name": candidate_name,
                    "raw_transcript": raw_transcript or candidate_name,
                },
            )
            if gemini_match:
                return customer_aliases.get(gemini_match.casefold())

            substring_matches = {
                c["CustomerID"]: dict(c)
                for c in customers
                if clean_name.casefold() in c["CustomerName"].casefold()
                or c["CustomerName"].casefold() in clean_name.casefold()
            }
            if len(substring_matches) == 1:
                return next(iter(substring_matches.values()))

            return None
        finally:
            if should_close:
                conn.close()

    def _match_postgres_customer(
        self, candidate_name: str, raw_transcript: str = ""
    ) -> Optional[Dict[str, Any]]:
        customers = self._postgres_customers()
        alias_to_customer = {}
        for customer in customers:
            for alias in (
                customer["CustomerName"],
                customer.get("CustomerNameHindi"),
            ):
                if alias:
                    alias_to_customer.setdefault(alias.casefold(), {})[
                        customer["CustomerID"]
                    ] = customer

        unique_aliases = {
            alias: next(iter(records.values()))
            for alias, records in alias_to_customer.items()
            if len(records) == 1
        }
        name = candidate_name.strip().casefold()
        if name in unique_aliases:
            return unique_aliases[name]

        from backend.app.gemini_understanding import resolve_catalog_entity

        resolved = resolve_catalog_entity(
            candidate_name,
            [
                alias
                for alias in unique_aliases
            ],
            "customer",
            {
                "spoken_name": candidate_name,
                "raw_transcript": raw_transcript or candidate_name,
            },
        )
        if resolved:
            return unique_aliases.get(resolved.casefold())

        substring_matches = {
            customer["CustomerID"]: customer
            for customer in customers
            if name in customer["CustomerName"].casefold()
            or customer["CustomerName"].casefold() in name
        }
        if len(substring_matches) == 1:
            return next(iter(substring_matches.values()))
        return None

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
        if self.use_postgres:
            return self._execute_postgres_order(
                items,
                customer_name=customer_name,
                payment_mode=payment_mode,
                raw_call_text=raw_call_text,
            )
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

                matched = self.match_inventory_item(
                    req_name,
                    conn=conn,
                    raw_transcript=raw_call_text,
                )
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
                matched_cust = self.match_customer(
                    cust_name_clean,
                    conn=conn,
                    raw_transcript=raw_call_text,
                )
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

    def _execute_postgres_order(
        self,
        items: List[Dict[str, Any]],
        customer_name: Optional[str] = None,
        payment_mode: str = "cash",
        raw_call_text: str = "",
    ) -> Dict[str, Any]:
        from backend.app.database import db
        from backend.app.models import StoreCredit, StoreInventory

        if not items:
            return {"status": "error", "message": "No order items specified."}

        store_id = self._active_store_id()
        try:
            order_lines = []
            total_amount = 0.0
            for entry in items:
                name = str(entry.get("name") or entry.get("entity") or "").strip()
                try:
                    quantity = int(entry.get("quantity", 1))
                except (TypeError, ValueError):
                    quantity = 1
                if quantity <= 0:
                    continue

                matched = self.match_inventory_item(
                    name,
                    raw_transcript=raw_call_text,
                )
                if not matched:
                    return {
                        "status": "error",
                        "message": f"Item '{name}' was not found in active inventory.",
                    }
                if int(matched["StockQuantity"]) < quantity:
                    return {
                        "status": "error",
                        "message": (
                            f"Insufficient stock for {matched['ItemName']}. "
                            f"Only {matched['StockQuantity']} available."
                        ),
                    }

                line_total = float(matched["Price"]) * quantity
                total_amount += line_total
                order_lines.append({
                    "item_id": matched["ItemID"],
                    "item_name": matched["ItemName"],
                    "quantity": quantity,
                    "unit_price": float(matched["Price"]),
                    "item_total": line_total,
                })

            if not order_lines:
                return {"status": "error", "message": "No valid order items to process."}

            locked_items = {}
            for line in order_lines:
                item = StoreInventory.query.filter_by(
                    store_id=store_id,
                    item_id=line["item_id"],
                    is_active=True,
                ).with_for_update().first()
                if not item:
                    raise ValueError(f"{line['item_name']} is no longer active.")
                if item.stock_quantity < line["quantity"]:
                    raise ValueError(
                        f"Insufficient stock for {item.item_name}. "
                        f"Only {item.stock_quantity} available."
                    )
                locked_items[item.item_id] = item

            for line in order_lines:
                item = locked_items[line["item_id"]]
                item.stock_quantity -= line["quantity"]
                line["new_stock"] = item.stock_quantity
                self._record_postgres_transaction(
                    raw_call_text or f"Call Order: {line['quantity']}x {line['item_name']}",
                    line["item_total"],
                    "Sale",
                    line["item_name"],
                    line["quantity"],
                )

            is_credit = str(payment_mode).lower() in ("udhaar", "credit")
            customer_name_clean = (customer_name or "").strip()
            new_customer_balance = None
            actual_customer_name = customer_name_clean
            if is_credit and customer_name_clean:
                matched_customer = self.match_customer(
                    customer_name_clean,
                    raw_transcript=raw_call_text,
                )
                if matched_customer:
                    customer = StoreCredit.query.filter_by(
                        store_id=store_id,
                        customer_id=matched_customer["CustomerID"],
                        is_active=True,
                    ).with_for_update().first()
                    if not customer:
                        raise ValueError("The customer account is no longer active.")
                    actual_customer_name = customer.customer_name
                    customer.outstanding_balance += total_amount
                    new_customer_balance = float(customer.outstanding_balance)
                else:
                    max_customer_id = db.session.query(
                        db.func.max(StoreCredit.customer_id)
                    ).filter_by(store_id=store_id).scalar() or 0
                    customer = StoreCredit(
                        store_id=store_id,
                        customer_id=max_customer_id + 1,
                        customer_name=customer_name_clean,
                        outstanding_balance=total_amount,
                        is_active=True,
                    )
                    db.session.add(customer)
                    actual_customer_name = customer_name_clean
                    new_customer_balance = total_amount

                self._record_postgres_transaction(
                    raw_call_text or f"Call Order Udhaar: Rs {total_amount:g} for {actual_customer_name}",
                    total_amount,
                    "Credit",
                    actual_customer_name,
                )

            db.session.commit()
            for line in order_lines:
                line.pop("new_stock", None)
            return {
                "status": "success",
                "action": "order_placed",
                "items": order_lines,
                "total_amount": total_amount,
                "payment_mode": "udhaar" if is_credit else "cash",
                "customer_name": actual_customer_name if is_credit else None,
                "new_balance": new_customer_balance,
                "message": (
                    f"Order placed successfully for Rs {total_amount:g} "
                    f"({len(order_lines)} item(s))."
                    + (
                        f" Logged to {actual_customer_name}'s udhaar."
                        if is_credit and customer_name_clean
                        else ""
                    )
                ),
            }
        except Exception as exc:
            db.session.rollback()
            return {"status": "error", "message": f"Database order failure: {str(exc)}"}

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

        if self.use_postgres:
            return self._execute_postgres_credit_log(
                cust_name,
                credit_amount,
                raw_call_text,
            )

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            matched_cust = self.match_customer(
                cust_name,
                conn=conn,
                raw_transcript=raw_call_text,
            )

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

    def _execute_postgres_credit_log(
        self, customer_name: str, amount: float, raw_call_text: str
    ) -> Dict[str, Any]:
        from backend.app.database import db
        from backend.app.models import StoreCredit

        store_id = self._active_store_id()
        try:
            matched = self.match_customer(
                customer_name,
                raw_transcript=raw_call_text,
            )
            if matched:
                customer = StoreCredit.query.filter_by(
                    store_id=store_id,
                    customer_id=matched["CustomerID"],
                    is_active=True,
                ).with_for_update().first()
                if not customer:
                    raise ValueError("The customer account is no longer active.")
                actual_name = customer.customer_name
                customer.outstanding_balance += amount
                new_balance = float(customer.outstanding_balance)
            else:
                max_customer_id = db.session.query(
                    db.func.max(StoreCredit.customer_id)
                ).filter_by(store_id=store_id).scalar() or 0
                actual_name = customer_name
                new_balance = amount
                db.session.add(StoreCredit(
                    store_id=store_id,
                    customer_id=max_customer_id + 1,
                    customer_name=actual_name,
                    outstanding_balance=new_balance,
                    is_active=True,
                ))

            self._record_postgres_transaction(
                raw_call_text or f"Call Udhaar Log: Rs {amount:g} for {actual_name}",
                amount,
                "Credit",
                actual_name,
            )
            db.session.commit()
            return {
                "status": "success",
                "action": "udhaar_logged",
                "customer_name": actual_name,
                "amount": amount,
                "new_balance": new_balance,
                "message": f"Logged Rs {amount:g} udhaar for {actual_name}. New balance: Rs {new_balance:g}.",
            }
        except Exception as exc:
            db.session.rollback()
            return {"status": "error", "message": f"Database credit failure: {str(exc)}"}

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

        if self.use_postgres:
            return self._execute_postgres_repayment(
                cust_name,
                repay_amount,
                raw_call_text,
            )

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            matched_cust = self.match_customer(
                cust_name,
                conn=conn,
                raw_transcript=raw_call_text,
            )
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

    def _execute_postgres_repayment(
        self, customer_name: str, amount: float, raw_call_text: str
    ) -> Dict[str, Any]:
        from backend.app.database import db
        from backend.app.models import StoreCredit

        store_id = self._active_store_id()
        try:
            matched = self.match_customer(
                customer_name,
                raw_transcript=raw_call_text,
            )
            if not matched:
                return {
                    "status": "error",
                    "message": f"Customer '{customer_name}' was not found in records.",
                }

            customer = StoreCredit.query.filter_by(
                store_id=store_id,
                customer_id=matched["CustomerID"],
                is_active=True,
            ).with_for_update().first()
            if not customer:
                raise ValueError("The customer account is no longer active.")
            actual_name = customer.customer_name
            customer.outstanding_balance = max(
                0.0,
                float(customer.outstanding_balance or 0) - amount,
            )
            new_balance = float(customer.outstanding_balance)
            self._record_postgres_transaction(
                raw_call_text or f"Call Repayment: Rs {amount:g} by {actual_name}",
                -amount,
                "Repayment",
                actual_name,
            )
            db.session.commit()
            return {
                "status": "success",
                "action": "repayment_recorded",
                "customer_name": actual_name,
                "amount": amount,
                "new_balance": new_balance,
                "message": f"Recorded Rs {amount:g} repayment from {actual_name}. Remaining balance: Rs {new_balance:g}.",
            }
        except Exception as exc:
            db.session.rollback()
            return {"status": "error", "message": f"Database repayment failure: {str(exc)}"}

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
