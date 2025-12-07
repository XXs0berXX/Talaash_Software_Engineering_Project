"""
User data model for Talash
Handles user information storage and retrieval with mobile number
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session
from app.db import Base
from datetime import datetime
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import re


class UserDB(Base):
    """SQLAlchemy User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    mobile = Column(String, nullable=False)  # NEW: Mobile number field
    role = Column(String, default="user", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserSignupRequest(BaseModel):
    """Pydantic model for user signup"""
    name: str
    email: str
    mobile: str  # NEW: Mobile field
    
    @validator('mobile')
    def validate_mobile(cls, v):
        """Validate mobile number format (Pakistani format)"""
        # Remove any spaces, dashes, or parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        
        # Check if it's a valid Pakistani mobile number
        # Format: 03XXXXXXXXX (11 digits) or +923XXXXXXXXX (13 digits with country code)
        if re.match(r'^03[0-9]{9}$', cleaned):
            return cleaned
        elif re.match(r'^\+923[0-9]{9}$', cleaned):
            return cleaned
        else:
            raise ValueError('Mobile number must be in format: 03XXXXXXXXX or +923XXXXXXXXX')
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@khi.iba.edu.pk",
                "mobile": "03001234567"
            }
        }


class UserResponse(BaseModel):
    """Pydantic model for user response"""
    id: int
    name: str
    email: str
    mobile: str  # NEW: Include mobile in response
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminSignupRequest(BaseModel):
    """Pydantic model for admin signup"""
    name: str
    email: str
    mobile: str  # NEW: Mobile field for admin
    admin_key: str  # Simple validation key for admin registration
    
    @validator('mobile')
    def validate_mobile(cls, v):
        """Validate mobile number format"""
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if re.match(r'^03[0-9]{9}$', cleaned) or re.match(r'^\+923[0-9]{9}$', cleaned):
            return cleaned
        else:
            raise ValueError('Mobile number must be in format: 03XXXXXXXXX or +923XXXXXXXXX')
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Admin User",
                "email": "admin@khi.iba.edu.pk",
                "mobile": "03001234567",
                "admin_key": "secret_admin_key"
            }
        }


def create_user(db: Session, name: str, email: str, mobile: str, role: str = "user") -> UserDB:
    """
    Create a new user in database
    
    Args:
        db: Database session
        name: User's name
        email: User's email
        mobile: User's mobile number
        role: User's role (default: "user")
        
    Returns:
        Created user object
    """
    db_user = UserDB(name=name, email=email, mobile=mobile, role=role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str) -> Optional[UserDB]:
    """
    Get user by email
    
    Args:
        db: Database session
        email: User's email
        
    Returns:
        User object or None if not found
    """
    return db.query(UserDB).filter(UserDB.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[UserDB]:
    """
    Get user by ID
    
    Args:
        db: Database session
        user_id: User's ID
        
    Returns:
        User object or None if not found
    """
    return db.query(UserDB).filter(UserDB.id == user_id).first()


def user_exists(db: Session, email: str) -> bool:
    """
    Check if user exists by email
    
    Args:
        db: Database session
        email: User's email
        
    Returns:
        True if user exists, False otherwise
    """
    return db.query(UserDB).filter(UserDB.email == email).first() is not None