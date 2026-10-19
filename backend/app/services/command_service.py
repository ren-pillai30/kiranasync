import sqlite3
import json
import uuid
from datetime import datetime, timezone

def ensure_pending_commands_schema(conn):
    """Ensure the PendingCommands table exists with needed columns and indexes."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS PendingCommands (
            CommandID TEXT PRIMARY KEY,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            ExpiresAt DATETIME,
            Operation TEXT NOT NULL,
            PayloadJSON TEXT NOT NULL,
            Status TEXT NOT NULL DEFAULT 'PENDING',
            CommittedTxnID INTEGER,
            RejectionReason TEXT
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_pending_status ON PendingCommands(Status)
    ''')
    conn.commit()

class CommandService:
    def __init__(self, db_path):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        ensure_pending_commands_schema(conn)
        return conn

    def create_pending_command(self, operation, payload, expires_in_seconds=300):
        """Create a new draft command that requires explicit user confirmation."""
        command_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        try:
            conn.execute('''
                INSERT INTO PendingCommands (CommandID, CreatedAt, Operation, PayloadJSON, Status)
                VALUES (?, ?, ?, ?, 'PENDING')
            ''', (command_id, created_at, operation, json.dumps(payload)))
            conn.commit()
        finally:
            conn.close()
            
        return {
            "CommandID": command_id,
            "Operation": operation,
            "Status": "PENDING",
            "Payload": payload
        }

    def get_command(self, command_id):
        """Fetch command status and details by CommandID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM PendingCommands WHERE CommandID = ?', (command_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "CommandID": row["CommandID"],
                "CreatedAt": row["CreatedAt"],
                "Operation": row["Operation"],
                "Payload": json.loads(row["PayloadJSON"]),
                "Status": row["Status"],
                "CommittedTxnID": row["CommittedTxnID"],
                "RejectionReason": row["RejectionReason"]
            }
        finally:
            conn.close()

    def cancel_command(self, command_id, reason="User cancelled"):
        """Cancel a pending command. Idempotent: returns success if already cancelled."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT Status FROM PendingCommands WHERE CommandID = ?', (command_id,))
            row = cursor.fetchone()
            if not row:
                return {"status": "error", "error": "Command not found"}
            if row["Status"] == "COMMITTED":
                return {"status": "error", "error": "Cannot cancel an already committed transaction"}
            if row["Status"] == "CANCELLED":
                return {"status": "success", "message": "Command was already cancelled"}

            cursor.execute('''
                UPDATE PendingCommands
                SET Status = 'CANCELLED', RejectionReason = ?
                WHERE CommandID = ? AND Status = 'PENDING'
            ''', (reason, command_id))
            conn.commit()
            return {"status": "success", "message": "Command successfully cancelled"}
        finally:
            conn.close()

    def confirm_command(self, command_id, execute_fn):
        """
        Atomically confirm and commit a command using execute_fn(conn, payload).
        Guarantees idempotency: duplicate confirmation requests return the existing result.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN IMMEDIATE')
            cursor.execute('SELECT * FROM PendingCommands WHERE CommandID = ?', (command_id,))
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return {"status": "error", "error": "Command not found"}

            status = row["Status"]
            if status == "COMMITTED":
                conn.rollback()
                return {
                    "status": "success",
                    "idempotent": True,
                    "message": "Transaction was already committed.",
                    "TxnID": row["CommittedTxnID"]
                }
            if status != "PENDING":
                conn.rollback()
                return {
                    "status": "error",
                    "error": f"Command is in '{status}' state and cannot be committed."
                }

            payload = json.loads(row["PayloadJSON"])
            try:
                # Execute the deterministic domain mutation
                commit_result = execute_fn(conn, payload, command_id)
                txn_id = commit_result.get("TxnID")

                cursor.execute('''
                    UPDATE PendingCommands
                    SET Status = 'COMMITTED', CommittedTxnID = ?
                    WHERE CommandID = ? AND Status = 'PENDING'
                ''', (txn_id, command_id))
                conn.commit()
                return {"status": "success", "idempotent": False, **commit_result}
            except Exception as e:
                conn.rollback()
                return {"status": "error", "error": str(e)}
        finally:
            conn.close()
