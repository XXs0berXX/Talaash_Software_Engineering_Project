"""
Claim Request Model
Handles claim requests that require admin approval
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Session, relationship
from app.db import Base
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


class ClaimRequestDB(Base):
    """SQLAlchemy Claim Request model"""
    __tablename__ = "claim_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("found_items.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User claiming
    
    # Claim details
    claimant_name = Column(String, nullable=False)
    claimant_email = Column(String, nullable=False)
    claimant_mobile = Column(String, nullable=False)
    notes = Column(Text, nullable=True)  # User's claim justification
    
    # Status tracking
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who reviewed
    admin_notes = Column(Text, nullable=True)  # Admin's review notes


# Pydantic Models

class ClaimRequestResponse(BaseModel):
    """Response model for claim request"""
    id: int
    item_id: int
    user_id: int
    claimant_name: str
    claimant_email: str
    claimant_mobile: str
    notes: Optional[str]
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime]
    admin_notes: Optional[str]
    
    class Config:
        from_attributes = True


class ClaimRequestWithItem(BaseModel):
    """Claim request with item details"""
    id: int
    item_id: int
    user_id: int
    claimant_name: str
    claimant_email: str
    claimant_mobile: str
    notes: Optional[str]
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime]
    admin_notes: Optional[str]
    
    # Item details
    item_description: str
    item_location: str
    item_date_found: datetime
    item_image_url: Optional[str]
    
    class Config:
        from_attributes = True


# Database Functions

def create_claim_request(
    db: Session,
    item_id: int,
    user_id: int,
    claimant_name: str,
    claimant_email: str,
    claimant_mobile: str,
    notes: Optional[str] = None
) -> ClaimRequestDB:
    """Create a new claim request"""
    claim_request = ClaimRequestDB(
        item_id=item_id,
        user_id=user_id,
        claimant_name=claimant_name,
        claimant_email=claimant_email,
        claimant_mobile=claimant_mobile,
        notes=notes
    )
    db.add(claim_request)
    db.commit()
    db.refresh(claim_request)
    return claim_request


def get_pending_claim_requests(db: Session, skip: int = 0, limit: int = 50) -> List[ClaimRequestDB]:
    """Get all pending claim requests"""
    return db.query(ClaimRequestDB).filter(
        ClaimRequestDB.status == "pending"
    ).offset(skip).limit(limit).all()


def get_claim_request_by_id(db: Session, claim_id: int) -> Optional[ClaimRequestDB]:
    """Get claim request by ID"""
    return db.query(ClaimRequestDB).filter(ClaimRequestDB.id == claim_id).first()


def approve_claim_request(
    db: Session,
    claim_id: int,
    admin_id: int,
    admin_notes: Optional[str] = None
) -> Optional[ClaimRequestDB]:
    """Approve a claim request"""
    claim = get_claim_request_by_id(db, claim_id)
    if claim:
        claim.status = "approved"
        claim.reviewed_at = datetime.utcnow()
        claim.reviewed_by = admin_id
        claim.admin_notes = admin_notes
        
        # Update the item status to claimed
        from app.models.item_model import get_found_item_by_id
        item = get_found_item_by_id(db, claim.item_id)
        if item:
            item.status = "claimed"
            item.claimed_by_name = claim.claimant_name
            item.claimed_by_email = claim.claimant_email
            item.claimed_by_mobile = claim.claimant_mobile
            item.claimed_at = datetime.utcnow()
            item.incident_report = admin_notes or "Claim approved by admin"
            item.incident_updated_at = datetime.utcnow()
            item.incident_updated_by = admin_id
        
        # Reject all other pending claims for this item
        other_claims = db.query(ClaimRequestDB).filter(
            ClaimRequestDB.item_id == claim.item_id,
            ClaimRequestDB.id != claim_id,
            ClaimRequestDB.status == "pending"
        ).all()
        
        for other_claim in other_claims:
            other_claim.status = "rejected"
            other_claim.reviewed_at = datetime.utcnow()
            other_claim.reviewed_by = admin_id
            other_claim.admin_notes = "Item claimed by another user"
        
        db.commit()
        db.refresh(claim)
    return claim


def reject_claim_request(
    db: Session,
    claim_id: int,
    admin_id: int,
    admin_notes: Optional[str] = None
) -> Optional[ClaimRequestDB]:
    """Reject a claim request"""
    claim = get_claim_request_by_id(db, claim_id)
    if claim:
        claim.status = "rejected"
        claim.reviewed_at = datetime.utcnow()
        claim.reviewed_by = admin_id
        claim.admin_notes = admin_notes
        db.commit()
        db.refresh(claim)
    return claim


def get_user_claim_requests(db: Session, user_id: int) -> List[ClaimRequestDB]:
    """Get all claim requests by a user"""
    return db.query(ClaimRequestDB).filter(
        ClaimRequestDB.user_id == user_id
    ).order_by(ClaimRequestDB.created_at.desc()).all()


def has_user_claimed_item(db: Session, user_id: int, item_id: int) -> bool:
    """Check if user has already submitted a claim for this item"""
    existing = db.query(ClaimRequestDB).filter(
        ClaimRequestDB.user_id == user_id,
        ClaimRequestDB.item_id == item_id,
        ClaimRequestDB.status == "pending"
    ).first()
    return existing is not None