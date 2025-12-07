"""
Item data model for Talash
Handles found and lost item storage and retrieval with incident reporting
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Session, relationship
from app.db import Base
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


class FoundItemDB(Base):
    """SQLAlchemy Found Item model"""
    __tablename__ = "found_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String, nullable=False)
    date_found = Column(DateTime, nullable=False)
    image_url = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, approved, claimed, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # NEW: Incident Report Fields
    incident_report = Column(Text, nullable=True)  # Admin's incident notes
    incident_updated_at = Column(DateTime, nullable=True)  # When incident was updated
    incident_updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who updated
    claimed_by_name = Column(String, nullable=True)  # Name of person who claimed
    claimed_by_email = Column(String, nullable=True)  # Email of person who claimed
    claimed_by_mobile = Column(String, nullable=True)  # Mobile of person who claimed
    claimed_at = Column(DateTime, nullable=True)  # When item was claimed


class LostItemDB(Base):
    """SQLAlchemy Lost Item model"""
    __tablename__ = "lost_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String, nullable=False)
    date_lost = Column(DateTime, nullable=False)
    image_url = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, approved, found, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # NEW: Incident Report Fields
    incident_report = Column(Text, nullable=True)
    incident_updated_at = Column(DateTime, nullable=True)
    incident_updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    found_at = Column(DateTime, nullable=True)  # When item was found


class FoundItemRequest(BaseModel):
    """Pydantic model for found item creation"""
    description: str
    location: str
    date_found: str  # ISO format: "2024-01-15T14:30:00"
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "Blue backpack with laptop",
                "location": "Main Library",
                "date_found": "2024-01-15T14:30:00"
            }
        }


class FoundItemResponse(BaseModel):
    """Pydantic model for found item response"""
    id: int
    user_id: int
    description: str
    location: str
    date_found: datetime
    image_url: Optional[str]
    status: str
    created_at: datetime
    incident_report: Optional[str] = None
    incident_updated_at: Optional[datetime] = None
    claimed_by_name: Optional[str] = None
    claimed_by_email: Optional[str] = None
    claimed_by_mobile: Optional[str] = None
    claimed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class FoundItemListResponse(BaseModel):
    """Pydantic model for found items list"""
    items: List[FoundItemResponse]
    total: int
    
    class Config:
        from_attributes = True


class LostItemRequest(BaseModel):
    """Pydantic model for lost item creation"""
    description: str
    location: str
    date_lost: str  # ISO format: "2024-01-15T14:30:00"
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "Red wallet with student ID",
                "location": "Cafeteria",
                "date_lost": "2024-01-14T12:00:00"
            }
        }


class LostItemResponse(BaseModel):
    """Pydantic model for lost item response"""
    id: int
    user_id: int
    description: str
    location: str
    date_lost: datetime
    image_url: Optional[str]
    status: str
    created_at: datetime
    incident_report: Optional[str] = None
    incident_updated_at: Optional[datetime] = None
    found_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class IncidentReportRequest(BaseModel):
    """Pydantic model for updating incident report"""
    incident_report: str
    claimed_by_name: Optional[str] = None
    claimed_by_email: Optional[str] = None
    claimed_by_mobile: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "incident_report": "Item claimed by student. Verified with ID card.",
                "claimed_by_name": "John Doe",
                "claimed_by_email": "john@khi.iba.edu.pk",
                "claimed_by_mobile": "03001234567"
            }
        }


def create_found_item(
    db: Session,
    user_id: int,
    description: str,
    location: str,
    date_found: datetime,
    image_url: Optional[str] = None
) -> FoundItemDB:
    """
    Create a new found item record
    
    Args:
        db: Database session
        user_id: ID of user reporting item
        description: Item description
        location: Location where item was found
        date_found: Date and time item was found
        image_url: Optional image URL
        
    Returns:
        Created found item object
    """
    db_item = FoundItemDB(
        user_id=user_id,
        description=description,
        location=location,
        date_found=date_found,
        image_url=image_url
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_found_items(db: Session, skip: int = 0, limit: int = 10) -> List[FoundItemDB]:
    """
    Get paginated list of found items
    
    Args:
        db: Database session
        skip: Number of items to skip
        limit: Number of items to return
        
    Returns:
        List of found items
    """
    return db.query(FoundItemDB).offset(skip).limit(limit).all()


def get_found_item_by_id(db: Session, item_id: int) -> Optional[FoundItemDB]:
    """
    Get found item by ID
    
    Args:
        db: Database session
        item_id: Item ID
        
    Returns:
        Found item object or None if not found
    """
    return db.query(FoundItemDB).filter(FoundItemDB.id == item_id).first()


def get_found_items_by_user(db: Session, user_id: int) -> List[FoundItemDB]:
    """
    Get all found items reported by a user
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        List of user's found items
    """
    return db.query(FoundItemDB).filter(FoundItemDB.user_id == user_id).all()


def update_incident_report(
    db: Session,
    item_id: int,
    admin_id: int,
    incident_report: str,
    claimed_by_name: Optional[str] = None,
    claimed_by_email: Optional[str] = None,
    claimed_by_mobile: Optional[str] = None
) -> Optional[FoundItemDB]:
    """
    Update incident report for a found item when claimed
    
    Args:
        db: Database session
        item_id: Item ID
        admin_id: Admin user ID who is updating
        incident_report: Incident description
        claimed_by_name: Name of person who claimed
        claimed_by_email: Email of person who claimed
        claimed_by_mobile: Mobile of person who claimed
        
    Returns:
        Updated found item object or None if not found
    """
    db_item = get_found_item_by_id(db, item_id)
    if db_item:
        db_item.incident_report = incident_report
        db_item.incident_updated_at = datetime.utcnow()
        db_item.incident_updated_by = admin_id
        db_item.status = "claimed"
        db_item.claimed_at = datetime.utcnow()
        
        if claimed_by_name:
            db_item.claimed_by_name = claimed_by_name
        if claimed_by_email:
            db_item.claimed_by_email = claimed_by_email
        if claimed_by_mobile:
            db_item.claimed_by_mobile = claimed_by_mobile
        
        db.commit()
        db.refresh(db_item)
    return db_item


def create_lost_item(
    db: Session,
    user_id: int,
    description: str,
    location: str,
    date_lost: datetime,
    image_url: Optional[str] = None
) -> LostItemDB:
    """
    Create a new lost item record
    
    Args:
        db: Database session
        user_id: ID of user reporting item
        description: Item description
        location: Location where item was lost
        date_lost: Date and time item was lost
        image_url: Optional image URL
        
    Returns:
        Created lost item object
    """
    db_item = LostItemDB(
        user_id=user_id,
        description=description,
        location=location,
        date_lost=date_lost,
        image_url=image_url
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_lost_items(db: Session, skip: int = 0, limit: int = 10) -> List[LostItemDB]:
    """
    Get paginated list of lost items
    
    Args:
        db: Database session
        skip: Number of items to skip
        limit: Number of items to return
        
    Returns:
        List of lost items
    """
    return db.query(LostItemDB).offset(skip).limit(limit).all()