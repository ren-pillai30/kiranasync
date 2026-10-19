import sqlite3


def ensure_archive_schema(conn):
    cursor = conn.cursor()
    for table in ("Inventory", "CustomerCredit"):
        columns = {
            row[1] for row in cursor.execute(f"PRAGMA table_info({table})")
        }
        if columns and "IsActive" not in columns:
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN IsActive INTEGER NOT NULL DEFAULT 1"
            )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS EntityArchive (
            ArchiveID INTEGER PRIMARY KEY AUTOINCREMENT,
            SourceTransactionID INTEGER UNIQUE,
            EntityType TEXT NOT NULL,
            EntityID INTEGER,
            EntityName TEXT NOT NULL,
            RemovalType TEXT NOT NULL,
            RemovedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            Reason TEXT,
            Quantity REAL,
            Balance REAL,
            RawCommand TEXT
        )
        """
    )
    transaction_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(Transactions)")
    }
    if {"TransactionType", "EntityName"} <= transaction_columns:
        quantity_expression = "Quantity" if "Quantity" in transaction_columns else "NULL"
        command_expression = "CommandText" if "CommandText" in transaction_columns else "NULL"
        timestamp_expression = (
            "coalesce(Timestamp, CURRENT_TIMESTAMP)"
            if "Timestamp" in transaction_columns
            else "CURRENT_TIMESTAMP"
        )
        cursor.execute(
            f"""
            INSERT OR IGNORE INTO EntityArchive (
                SourceTransactionID, EntityType, EntityName, RemovalType,
                RemovedAt, Quantity, RawCommand
            )
            SELECT rowid,
                   CASE WHEN TransactionType = 'WriteOff' THEN 'Product' ELSE 'Customer' END,
                   EntityName,
                   TransactionType,
                   {timestamp_expression},
                   {quantity_expression},
                   {command_expression}
            FROM Transactions
            WHERE TransactionType IN ('WriteOff', 'CustomerArchived')
              AND EntityName IS NOT NULL
            """
        )
    conn.commit()


def init_db():
    conn = sqlite3.connect('kirana.db')
    cursor = conn.cursor()

    # 1. Inventory Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Inventory (
            ItemID INTEGER PRIMARY KEY AUTOINCREMENT,
            ItemName TEXT NOT NULL UNIQUE,
            Category TEXT,
            StockQuantity INTEGER NOT NULL,
            Price REAL NOT NULL
        )
    ''')

    # 2. Customer Credit (Udhaar) Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS CustomerCredit (
            CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
            CustomerName TEXT NOT NULL UNIQUE,
            PhoneNumber TEXT,
            OutstandingBalance REAL DEFAULT 0.0
        )
    ''')
    ensure_archive_schema(conn)

    # 3. Transaction Logging Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Transactions (
            TxnID INTEGER PRIMARY KEY AUTOINCREMENT,
            Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            CommandText TEXT,
            TotalAmount REAL,
            TransactionType TEXT,
            EntityName TEXT,
            Quantity REAL
        )
    ''')
    transaction_columns = {
        row[1] for row in cursor.execute('PRAGMA table_info(Transactions)')
    }
    for column, column_type in (
        ('TransactionType', 'TEXT'),
        ('EntityName', 'TEXT'),
        ('Quantity', 'REAL'),
    ):
        if column not in transaction_columns:
            cursor.execute(
                f'ALTER TABLE Transactions ADD COLUMN {column} {column_type}'
            )

    # Insert some dummy inventory for testing
    try:
        cursor.executemany('''
            INSERT INTO Inventory (ItemName, Category, StockQuantity, Price)
            VALUES (?, ?, ?, ?)
        ''', [
            ('Tata Salt 1kg', 'Staples', 50, 25.0),
            ('Sugar 1kg', 'Staples', 30, 45.0),
            ('Maggi 70g', 'Snacks', 100, 14.0),
            ('Fortune Sunflower Oil 1L', 'Staples', 20, 145.0)
        ])
        
        cursor.execute("INSERT INTO CustomerCredit (CustomerName, PhoneNumber, OutstandingBalance) VALUES ('Ramesh', '9876543210', 0.0)")
    except sqlite3.IntegrityError:
        pass # Ignore if dummy data already exists

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()