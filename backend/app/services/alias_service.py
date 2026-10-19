import sqlite3
import re

def ensure_aliases_schema(conn):
    """Ensures the Aliases table exists with proper indexes."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS Aliases (
            AliasID INTEGER PRIMARY KEY AUTOINCREMENT,
            EntityType TEXT NOT NULL, -- 'Product' or 'Customer'
            EntityID INTEGER NOT NULL,
            ResolvedName TEXT NOT NULL,
            SpokenAlias TEXT NOT NULL UNIQUE,
            IsApproved INTEGER DEFAULT 1,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_spoken_alias ON Aliases(SpokenAlias)')
    conn.commit()

class AliasService:
    def __init__(self, db_path):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        ensure_aliases_schema(conn)
        return conn

    def add_alias(self, entity_type, entity_id, resolved_name, spoken_alias):
        """Add an approved alias for a product or customer, verifying target IDs and rejecting conflicting mappings."""
        clean_alias = spoken_alias.strip().lower()
        if not clean_alias:
            return {"status": "error", "error": "Spoken alias cannot be empty"}
        if entity_type not in {"Product", "Customer"}:
            return {"status": "error", "error": f"Invalid entity type '{entity_type}'. Must be 'Product' or 'Customer'"}

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # 1. Verify target exists in DB
            if entity_type == "Product":
                cursor.execute("SELECT ItemName FROM Inventory WHERE ItemID = ?", (entity_id,))
                row = cursor.fetchone()
                if not row:
                    return {"status": "error", "error": f"Product ID {entity_id} does not exist in Inventory"}
                if row["ItemName"].lower() != resolved_name.strip().lower():
                    # Align with actual canonical name in database
                    resolved_name = row["ItemName"]
            elif entity_type == "Customer":
                cursor.execute("SELECT CustomerName FROM CustomerCredit WHERE CustomerID = ?", (entity_id,))
                row = cursor.fetchone()
                if not row:
                    return {"status": "error", "error": f"Customer ID {entity_id} does not exist in CustomerCredit"}
                if row["CustomerName"].lower() != resolved_name.strip().lower():
                    resolved_name = row["CustomerName"]

            # 2. Check for conflicting mappings
            cursor.execute("SELECT EntityType, EntityID, ResolvedName FROM Aliases WHERE SpokenAlias = ?", (clean_alias,))
            existing = cursor.fetchone()
            if existing:
                if existing["EntityType"] != entity_type or existing["EntityID"] != entity_id:
                    return {
                        "status": "error",
                        "error": f"Conflicting alias: '{clean_alias}' is already mapped to {existing['EntityType']} '{existing['ResolvedName']}' (ID: {existing['EntityID']}). Cannot remap without deleting existing mapping."
                    }
                # Already correctly mapped
                return {"status": "success", "message": f"Alias '{clean_alias}' -> '{resolved_name}' already active"}

            # 3. Insert alias
            cursor.execute('''
                INSERT INTO Aliases (EntityType, EntityID, ResolvedName, SpokenAlias, IsApproved)
                VALUES (?, ?, ?, ?, 1)
            ''', (entity_type, entity_id, resolved_name, clean_alias))
            conn.commit()
            return {"status": "success", "message": f"Added alias '{clean_alias}' -> '{resolved_name}'"}
        finally:
            conn.close()

    def resolve_alias(self, spoken_text):
        """
        Check if any token sequence in spoken_text matches an approved alias.
        Verifies target entity still exists in DB.
        Clarifies rather than guesses if multiple conflicting aliases match.
        """
        clean_text = spoken_text.strip().lower()
        if not clean_text:
            return {"Found": False}

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT AliasID, EntityType, EntityID, ResolvedName, SpokenAlias FROM Aliases WHERE IsApproved = 1')
            rows = cursor.fetchall()
            
            matches = []
            for row in rows:
                alias = row["SpokenAlias"].lower()
                # Check for exact string or word boundary match
                if alias == clean_text or re.search(rf'\b{re.escape(alias)}\b', clean_text):
                    matches.append(row)

            if not matches:
                return {"Found": False}

            # Check if all matches refer to the same target entity
            distinct_targets = {(m["EntityType"], m["EntityID"], m["ResolvedName"]) for m in matches}
            if len(distinct_targets) > 1:
                return {
                    "Found": False,
                    "Ambiguous": True,
                    "Message": f"Spoken phrase matches multiple conflicting aliases. Clarification required.",
                    "Candidates": [
                        {"EntityType": m["EntityType"], "EntityID": m["EntityID"], "ResolvedName": m["ResolvedName"], "SpokenAlias": m["SpokenAlias"]}
                        for m in matches
                    ]
                }

            best_match = matches[0]
            # Verify target still exists in DB
            if best_match["EntityType"] == "Product":
                cursor.execute("SELECT ItemName FROM Inventory WHERE ItemID = ?", (best_match["EntityID"],))
                if not cursor.fetchone():
                    return {"Found": False, "Error": f"Target product for alias '{best_match['SpokenAlias']}' no longer exists in inventory"}
            elif best_match["EntityType"] == "Customer":
                cursor.execute("SELECT CustomerName FROM CustomerCredit WHERE CustomerID = ?", (best_match["EntityID"],))
                if not cursor.fetchone():
                    return {"Found": False, "Error": f"Target customer for alias '{best_match['SpokenAlias']}' no longer exists in credit ledger"}

            return {
                "Found": True,
                "ResolvedName": best_match["ResolvedName"],
                "EntityType": best_match["EntityType"],
                "EntityID": best_match["EntityID"],
                "MatchedAlias": best_match["SpokenAlias"]
            }
        finally:
            conn.close()

    def list_aliases(self):
        """List all approved aliases."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT AliasID, EntityType, EntityID, ResolvedName, SpokenAlias, CreatedAt FROM Aliases ORDER BY CreatedAt DESC')
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def delete_alias(self, alias_id):
        """Delete an alias by ID."""
        conn = self._get_connection()
        try:
            conn.execute('DELETE FROM Aliases WHERE AliasID = ?', (alias_id,))
            conn.commit()
            return {"status": "success"}
        finally:
            conn.close()
