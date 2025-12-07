"""
Script to check all items in the database
Run: python check_items.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/talash.db")

print("\n" + "="*80)
print("CHECKING DATABASE:", DATABASE_URL)
print("="*80)

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Check FOUND items
    print("\n" + "="*80)
    print("FOUND ITEMS:")
    print("="*80)
    
    found_items = db.execute(text("""
        SELECT f.id, f.description, f.location, f.status, f.created_at, u.email 
        FROM found_items f 
        LEFT JOIN users u ON f.user_id = u.id
    """)).fetchall()
    
    if not found_items:
        print("❌ No found items in database")
    else:
        for item in found_items:
            item_id, desc, location, status, created, email = item
            status_badge = "⏳" if status == "pending" else "✅" if status == "approved" else "❌"
            print(f"\n{status_badge} ID: {item_id}")
            print(f"   Description: {desc[:50]}...")
            print(f"   Location: {location}")
            print(f"   Status: {status}")
            print(f"   Reported by: {email}")
            print(f"   Created: {created}")
            print("-" * 80)
    
    # Check LOST items
    print("\n" + "="*80)
    print("LOST ITEMS:")
    print("="*80)
    
    lost_items = db.execute(text("""
        SELECT l.id, l.description, l.location, l.status, l.created_at, u.email 
        FROM lost_items l 
        LEFT JOIN users u ON l.user_id = u.id
    """)).fetchall()
    
    if not lost_items:
        print("❌ No lost items in database")
    else:
        for item in lost_items:
            item_id, desc, location, status, created, email = item
            status_badge = "⏳" if status == "pending" else "✅" if status == "approved" else "❌"
            print(f"\n{status_badge} ID: {item_id}")
            print(f"   Description: {desc[:50]}...")
            print(f"   Location: {location}")
            print(f"   Status: {status}")
            print(f"   Reported by: {email}")
            print(f"   Created: {created}")
            print("-" * 80)
    
    # Statistics
    found_pending = db.execute(text("SELECT COUNT(*) FROM found_items WHERE status='pending'")).scalar()
    found_approved = db.execute(text("SELECT COUNT(*) FROM found_items WHERE status='approved'")).scalar()
    lost_pending = db.execute(text("SELECT COUNT(*) FROM lost_items WHERE status='pending'")).scalar()
    lost_approved = db.execute(text("SELECT COUNT(*) FROM lost_items WHERE status='approved'")).scalar()
    
    print("\n" + "="*80)
    print("📊 STATISTICS:")
    print("="*80)
    print(f"\nFOUND ITEMS:")
    print(f"   Total: {len(found_items)}")
    print(f"   Pending: {found_pending}")
    print(f"   Approved: {found_approved}")
    
    print(f"\nLOST ITEMS:")
    print(f"   Total: {len(lost_items)}")
    print(f"   Pending: {lost_pending}")
    print(f"   Approved: {lost_approved}")
    
    print("="*80 + "\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()