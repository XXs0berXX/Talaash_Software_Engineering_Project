"""
Script to check admin users in the database
Run this in your backend directory: python check_admin.py
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
    # Query all users
    result = db.execute(text("SELECT id, name, email, role FROM users"))
    users = result.fetchall()
    
    print("\nALL USERS IN DATABASE:")
    print("="*80)
    
    if not users:
        print("❌ No users found in database!")
        print("\n⚠️  You need to create an admin user first!")
        print("Run: python create_admin.py")
    else:
        for user in users:
            user_id, name, email, role = user
            admin_badge = " ⭐ ADMIN" if role == "admin" else ""
            print(f"\n{'='*80}")
            print(f"ID: {user_id}")
            print(f"Name: {name}")
            print(f"Email: {email}")
            print(f"Role: {role}{admin_badge}")
        
        print(f"\n{'='*80}")
    
    # Count admins
    admin_count = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin'")).scalar()
    total_count = len(users)
    
    print(f"\n📊 STATISTICS:")
    print(f"   Total users: {total_count}")
    print(f"   Admin users: {admin_count}")
    print(f"   Regular users: {total_count - admin_count}")
    
    if admin_count == 0:
        print("\n⚠️  WARNING: No admin users found!")
        print("   Run: python create_admin.py")
    
    print("="*80 + "\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()