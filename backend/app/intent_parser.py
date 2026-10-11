import sqlite3
import re

DB_PATH = 'kirana.db'

def parse_and_execute(transcript):
    transcript = transcript.lower()
    response_msg = ""
    
    # 1. Check for "Udhaar" / Credit intent
    if "khaate" in transcript or "udhaar" in transcript or "add kar do" in transcript:
        # Extract amount (e.g., "250" or "dhai sau")
        # For simplicity in this demo, let's look for numbers
        numbers = re.findall(r'\d+', transcript)
        amount = int(numbers[0]) if numbers else 250 # Fallback to 250 for testing
        
        # Hardcoding 'Ramesh' for demo, but you could extract names too
        customer = 'Ramesh' 
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE CustomerCredit 
            SET OutstandingBalance = OutstandingBalance + ? 
            WHERE CustomerName = ?
        ''', (amount, customer))
        conn.commit()
        
        # Log the transaction
        cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (transcript, amount))
        conn.commit()
        conn.close()
        
        return {"status": "success", "action": "udhaar_added", "message": f"Added Rs {amount} to {customer}'s account."}

    # 2. Check for Inventory / Selling intent
    elif "tata salt" in transcript or "namak" in transcript:
        item_name = 'Tata Salt 1kg'
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current stock and price
        cursor.execute('SELECT StockQuantity, Price FROM Inventory WHERE ItemName = ?', (item_name,))
        result = cursor.fetchone()
        
        if result and result[0] > 0:
            new_stock = result[0] - 1
            price = result[1]
            
            # Update stock
            cursor.execute('UPDATE Inventory SET StockQuantity = ? WHERE ItemName = ?', (new_stock, item_name))
            conn.commit()
            
            # Log transaction
            cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (transcript, price))
            conn.commit()
            conn.close()
            
            return {"status": "success", "action": "inventory_updated", "message": f"Sold 1 {item_name}. Stock left: {new_stock}."}
        else:
            conn.close()
            return {"status": "failed", "action": "out_of_stock", "message": f"{item_name} is out of stock!"}
            
    else:
        return {"status": "unrecognized", "message": "Could not understand the command."}