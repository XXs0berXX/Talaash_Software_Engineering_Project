"""
Database migration script to create claim_requests table
Run this script once to add the new table to your database
"""

import sqlite3
import os
from datetime import datetime

# Path to your database
DB_PATH = "database/talash.db"

def run_migration():
    """Create the claim_requests table using raw SQL"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return
    
    print(f"📦 Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("\n🔄 Starting migration...\n")
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='claim_requests'
        """)
        
        if cursor.fetchone():
            print("⚠️  claim_requests table already exists!")
            response = input("Drop and recreate? (yes/no): ")
            if response.lower() in ['yes', 'y']:
                cursor.execute("DROP TABLE claim_requests")
                print("   🗑️  Dropped existing table")
            else:
                print("❌ Migration cancelled")
                return
        
        # Create claim_requests table
        print("1️⃣ Creating claim_requests table...")
        cursor.execute("""
            CREATE TABLE claim_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                claimant_name VARCHAR NOT NULL,
                claimant_email VARCHAR NOT NULL,
                claimant_mobile VARCHAR NOT NULL,
                notes TEXT,
                status VARCHAR DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER,
                admin_notes TEXT,
                FOREIGN KEY (item_id) REFERENCES found_items(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (reviewed_by) REFERENCES users(id)
            )
        """)
        print("   ✅ Table created successfully")
        
        # Create indexes for better query performance
        print("\n2️⃣ Creating indexes...")
        
        indexes = [
            ("idx_claim_requests_item_id", "item_id"),
            ("idx_claim_requests_user_id", "user_id"),
            ("idx_claim_requests_status", "status"),
            ("idx_claim_requests_created_at", "created_at")
        ]
        
        for idx_name, column in indexes:
            cursor.execute(f"""
                CREATE INDEX {idx_name} 
                ON claim_requests({column})
            """)
            print(f"   ✅ Created index: {idx_name}")
        
        # Commit changes
        conn.commit()
        print("\n" + "="*50)
        print("✅ Migration completed successfully!")
        print("="*50)
        
        # Verify the table
        print("\n📋 Verifying table structure...\n")
        cursor.execute("PRAGMA table_info(claim_requests)")
        columns = cursor.fetchall()
        
        print("claim_requests table columns:")
        for col in columns:
            col_id, name, col_type, not_null, default, pk = col
            nullable = "NOT NULL" if not_null else "NULL"
            pk_str = " (PRIMARY KEY)" if pk else ""
            default_str = f" DEFAULT {default}" if default else ""
            print(f"  - {name} ({col_type}) {nullable}{default_str}{pk_str}")
        
        # Show indexes
        print("\nIndexes:")
        cursor.execute("PRAGMA index_list(claim_requests)")
        for idx in cursor.fetchall():
            print(f"  - {idx[1]}")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()
        print("\n🔒 Database connection closed")


if __name__ == "__main__":
    print("="*50)
    print("   DATABASE MIGRATION SCRIPT")
    print("   Creating claim_requests table")
    print("="*50)
    
    response = input("\n⚠️  This will modify your database. Continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        run_migration()
    else:
        print("❌ Migration cancelled")