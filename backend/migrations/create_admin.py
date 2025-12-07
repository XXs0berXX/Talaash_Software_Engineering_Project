"""
Script to create/promote a user to admin in the database
For Firebase Authentication users only!

IMPORTANT: The user must already exist in Firebase Authentication
This script only updates their role in the local database

Run this in your backend directory: python create_admin.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/talash.db")

print("\n" + "="*80)
print("PROMOTE USER TO ADMIN - TAALASH PORTAL")
print("="*80)
print(f"Database: {DATABASE_URL}")
print("="*80 + "\n")

print("⚠️  IMPORTANT: This script is for Firebase Authentication users")
print("   The user must already be registered in Firebase!")
print("   If not, sign up through your portal first.\n")
print("="*80 + "\n")

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Show current admins
    admin_count = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin'")).scalar()
    
    if admin_count > 0:
        print(f"📊 Current admin users: {admin_count}")
        admins = db.execute(text("SELECT name, email FROM users WHERE role = 'admin'")).fetchall()
        for admin in admins:
            print(f"   - {admin[0]} ({admin[1]})")
        print()
    
    # Get email to promote
    print("📝 Enter the email of the user to promote to admin:")
    print("-" * 80)
    
    while True:
        email = input("\nEmail: ").strip().lower()
        if validate_email(email):
            break
        print("❌ Invalid email format")
    
    # Check if user exists
    existing = db.execute(
        text("SELECT id, name, email, role FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()
    
    if existing:
        user_id, name, user_email, current_role = existing
        
        if current_role == 'admin':
            print(f"\n✅ {name} ({email}) is already an admin!")
            print("="*80 + "\n")
        else:
            # Update to admin
            db.execute(
                text("UPDATE users SET role = 'admin' WHERE email = :email"),
                {"email": email}
            )
            db.commit()
            
            print("\n" + "="*80)
            print("✅ USER PROMOTED TO ADMIN SUCCESSFULLY!")
            print("="*80)
            print(f"\n👤 Name: {name}")
            print(f"📧 Email: {email}")
            print(f"🔑 Role: admin (updated from {current_role})")
            print("\n" + "="*80)
            print("\n✨ User can now log in with admin privileges!")
            print("="*80 + "\n")
    else:
        # User doesn't exist in database - offer to create
        print(f"\n⚠️  User with email '{email}' not found in database!")
        print("\n❓ This could mean:")
        print("   1. The user hasn't signed up in Firebase yet")
        print("   2. The user signed up but wasn't added to the database")
        
        response = input("\n❓ Do you want to create this user as admin? (yes/no): ").lower().strip()
        
        if response in ['yes', 'y']:
            name = input("\nEnter user's full name: ").strip()
            
            if name and len(name) >= 2:
                db.execute(
                    text("""
                        INSERT INTO users (name, email, role, created_at)
                        VALUES (:name, :email, 'admin', CURRENT_TIMESTAMP)
                    """),
                    {
                        "name": name,
                        "email": email
                    }
                )
                db.commit()
                
                print("\n" + "="*80)
                print("✅ ADMIN USER CREATED SUCCESSFULLY!")
                print("="*80)
                print(f"\n👤 Name: {name}")
                print(f"📧 Email: {email}")
                print(f"🔑 Role: admin")
                print("\n" + "="*80)
                print("\n⚠️  IMPORTANT: Make sure this user is registered in Firebase!")
                print("   They must sign up through your portal to log in.")
                print("="*80 + "\n")
            else:
                print("\n❌ Invalid name. Operation cancelled.")
        else:
            print("\n❌ Operation cancelled.")
            print("   Please have the user sign up first, then run this script again.")
    
except Exception as e:
    db.rollback()
    print(f"\n❌ ERROR: Failed to update user")
    print(f"Details: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()