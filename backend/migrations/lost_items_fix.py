"""
Database migration script to fix lost items statuses
Run this once to update existing data
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Database connection (adjust this to your database URL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./talash.db")

def migrate_lost_items_status():
    """
    Update existing lost items:
    1. Change all "pending" status to "active" (since we removed admin approval)
    2. Keep "found" status as is
    3. Keep "rejected" status as is (if you want to clean them up, you can)
    """
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Update pending items to active
        result = db.execute(
            text("UPDATE lost_items SET status = 'active' WHERE status = 'pending'")
        )
        db.commit()
        
        print(f"✅ Updated {result.rowcount} lost items from 'pending' to 'active'")
        
        # Optional: Remove old rejected items (if you want)
        # Uncomment the following lines if you want to delete rejected items
        # result = db.execute(
        #     text("DELETE FROM lost_items WHERE status = 'rejected'")
        # )
        # db.commit()
        # print(f"🗑️  Deleted {result.rowcount} rejected lost items")
        
        # Show current status distribution
        result = db.execute(
            text("""
                SELECT status, COUNT(*) as count 
                FROM lost_items 
                GROUP BY status
            """)
        )
        
        print("\n📊 Current lost items status distribution:")
        for row in result:
            print(f"   {row.status}: {row.count}")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔄 Starting lost items status migration...")
    migrate_lost_items_status()
    print("\n✅ Migration complete!")