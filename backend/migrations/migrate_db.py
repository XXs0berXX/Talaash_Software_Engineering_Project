"""
Database migration script to add mobile number and incident report fields
Run this once to update your existing database schema
"""

import sqlite3
import os

# Path to your database
DB_PATH = "database/talash.db"

def run_migration():
    """Run database migration to add new columns"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return
    
    print(f"📦 Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("\n🔄 Starting migration...\n")
        
        # ============ USER TABLE MIGRATION ============
        print("1️⃣ Adding mobile column to users table...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN mobile VARCHAR")
            print("   ✅ Mobile column added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("   ⚠️  Mobile column already exists, skipping")
            else:
                raise
        
        # Set default mobile for existing users
        print("2️⃣ Setting default mobile for existing users...")
        cursor.execute("UPDATE users SET mobile = '03000000000' WHERE mobile IS NULL")
        affected = cursor.rowcount
        print(f"   ✅ Updated {affected} existing user(s)")
        
        # ============ FOUND ITEMS TABLE MIGRATION ============
        print("\n3️⃣ Adding incident report columns to found_items table...")
        
        columns_to_add = [
            ("incident_report", "TEXT"),
            ("incident_updated_at", "TIMESTAMP"),
            ("incident_updated_by", "INTEGER"),
            ("claimed_by_name", "VARCHAR"),
            ("claimed_by_email", "VARCHAR"),
            ("claimed_by_mobile", "VARCHAR"),
            ("claimed_at", "TIMESTAMP")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE found_items ADD COLUMN {col_name} {col_type}")
                print(f"   ✅ Added {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f"   ⚠️  {col_name} already exists, skipping")
                else:
                    raise
        
        # ============ LOST ITEMS TABLE MIGRATION ============
        print("\n4️⃣ Adding incident report columns to lost_items table...")
        
        lost_columns = [
            ("incident_report", "TEXT"),
            ("incident_updated_at", "TIMESTAMP"),
            ("incident_updated_by", "INTEGER"),
            ("found_at", "TIMESTAMP")
        ]
        
        for col_name, col_type in lost_columns:
            try:
                cursor.execute(f"ALTER TABLE lost_items ADD COLUMN {col_name} {col_type}")
                print(f"   ✅ Added {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f"   ⚠️  {col_name} already exists, skipping")
                else:
                    raise
        
        # Commit changes
        conn.commit()
        print("\n" + "="*50)
        print("✅ Migration completed successfully!")
        print("="*50)
        
        # Verify changes
        print("\n📋 Verifying schema changes...\n")
        
        cursor.execute("PRAGMA table_info(users)")
        users_cols = cursor.fetchall()
        print("Users table columns:")
        for col in users_cols:
            print(f"  - {col[1]} ({col[2]})")
        
        print("\nFound Items incident columns:")
        cursor.execute("PRAGMA table_info(found_items)")
        found_cols = [col for col in cursor.fetchall() if 'incident' in col[1] or 'claimed' in col[1]]
        for col in found_cols:
            print(f"  - {col[1]} ({col[2]})")
        
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
    print("   Adding mobile & incident report fields")
    print("="*50)
    
    response = input("\n⚠️  This will modify your database. Continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        run_migration()
    else:
        print("❌ Migration cancelled")