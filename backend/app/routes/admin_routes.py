"""
Admin routes for administrative operations
Handles admin signup, login, item moderation, and incident reports
"""

import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, Query, Header, File, UploadFile, Form
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from app.db import get_db
from app.models.user_model import (
    AdminSignupRequest,
    UserResponse,
    create_user,
    get_user_by_email,
    get_user_by_id,
    user_exists
)
from app.utils.validators import validate_iba_email
from app.utils.firebase_verify import (
    extract_token_from_header,
    get_user_from_token,
    initialize_firebase
)
from app.models.claim_request_model import (
    get_pending_claim_requests,
    get_claim_request_by_id,
    approve_claim_request,
    reject_claim_request,
    ClaimRequestDB
)
from app.models.item_model import FoundItemDB

router = APIRouter()

# Simple admin key for registration (should be environment variable in production)
ADMIN_KEY = os.getenv("ADMIN_KEY", "admin_secret_2024")

initialize_firebase()


# Pydantic models
class AdminLoginRequest(BaseModel):
    email: str
    token: str


class IncidentReportRequest(BaseModel):
    """Request body for incident report"""
    incident_report: str
    claimed_by_name: Optional[str] = None
    claimed_by_email: Optional[str] = None
    claimed_by_mobile: Optional[str] = None


class ClaimReviewRequest(BaseModel):
    """Request body for reviewing a claim"""
    admin_notes: Optional[str] = None


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_signup(
    request: AdminSignupRequest,
    db: Session = Depends(get_db)
):
    """Admin signup endpoint"""
    
    if request.admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin registration key"
        )
    
    if not validate_iba_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only @khi.iba.edu.pk email addresses are allowed"
        )
    
    if user_exists(db, request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    db_user = create_user(
        db=db,
        name=request.name,
        email=request.email,
        mobile=request.mobile,
        role="admin"
    )
    
    return db_user


@router.post("/login")
def admin_login(
    request: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """Admin login endpoint"""
    
    if not validate_iba_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email domain"
        )
    
    user_data = get_user_from_token(request.token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, request.email)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )
    
    if db_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    
    return {
        "status": "success",
        "admin": {
            "id": db_user.id,
            "name": db_user.name,
            "email": db_user.email,
            "role": db_user.role
        },
        "redirect": "/admin/dashboard"
    }


@router.get("/dashboard")
def admin_dashboard(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """Admin dashboard data endpoint with claim requests"""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    user_data = get_user_from_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user or db_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    
    from app.models.item_model import FoundItemDB, LostItemDB
    
    # Get statistics
    pending_items = db.query(func.count(FoundItemDB.id)).filter(FoundItemDB.status == "pending").scalar()
    total_items = db.query(func.count(FoundItemDB.id)).scalar()
    approved_items = db.query(func.count(FoundItemDB.id)).filter(FoundItemDB.status == "approved").scalar()
    rejected_items = db.query(func.count(FoundItemDB.id)).filter(FoundItemDB.status == "rejected").scalar()
    claimed_items = db.query(func.count(FoundItemDB.id)).filter(FoundItemDB.status == "claimed").scalar()
    
    pending_lost_items = db.query(func.count(LostItemDB.id)).filter(LostItemDB.status == "active").scalar()
    total_lost_items = db.query(func.count(LostItemDB.id)).scalar()
    approved_lost_items = db.query(func.count(LostItemDB.id)).filter(LostItemDB.status == "approved").scalar()
    
    pending_claims = db.query(func.count(ClaimRequestDB.id)).filter(ClaimRequestDB.status == "pending").scalar()
    
    return {
        "status": "success",
        "admin": {
            "id": db_user.id,
            "name": db_user.name,
            "email": db_user.email
        },
        "statistics": {
            "pending_items": pending_items or 0,
            "total_items": total_items or 0,
            "approved_items": approved_items or 0,
            "rejected_items": rejected_items or 0,
            "claimed_items": claimed_items or 0,
            "pending_lost_items": pending_lost_items or 0,
            "total_lost_items": total_lost_items or 0,
            "approved_lost_items": approved_lost_items or 0,
            "pending_claim_requests": pending_claims or 0
        }
    }


@router.get("/claims/pending")
def get_pending_claims(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get all pending claim requests with item details"""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    user_data = get_user_from_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user or db_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    
    claims = get_pending_claim_requests(db, skip, limit)
    
    # Enrich with item and user details
    result = []
    for claim in claims:
        item = db.query(FoundItemDB).filter(FoundItemDB.id == claim.item_id).first()
        claimant = get_user_by_id(db, claim.user_id)
        
        if not item or not claimant:
            continue
            
        result.append({
            "claim_id": claim.id,
            "created_at": claim.created_at.isoformat(),
            "claimant": {
                "user_id": claimant.id,
                "name": claim.claimant_name,
                "email": claim.claimant_email,
                "mobile": claim.claimant_mobile,
                "notes": claim.notes
            },
            "item": {
                "id": item.id,
                "description": item.description,
                "location": item.location,
                "date_found": item.date_found.isoformat() if item.date_found else None,
                "image_url": item.image_url,
                "status": item.status
            }
        })
    
    return {
        "status": "success",
        "claims": result,
        "total": len(result)
    }


@router.post("/claims/{claim_id}/approve")
def approve_claim(
    claim_id: int,
    request: ClaimReviewRequest,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """Approve a claim request"""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    user_data = get_user_from_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user or db_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    
    claim = get_claim_request_by_id(db, claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim request not found"
        )
    
    if claim.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Claim has already been {claim.status}"
        )
    
    updated_claim = approve_claim_request(
        db=db,
        claim_id=claim_id,
        admin_id=db_user.id,
        admin_notes=request.admin_notes
    )
    
    return {
        "status": "success",
        "message": "Claim approved successfully. Item has been marked as claimed.",
        "claim": {
            "id": updated_claim.id,
            "status": updated_claim.status,
            "reviewed_at": updated_claim.reviewed_at.isoformat() if updated_claim.reviewed_at else None,
            "admin_notes": updated_claim.admin_notes
        }
    }


@router.post("/claims/{claim_id}/reject")
def reject_claim(
    claim_id: int,
    request: ClaimReviewRequest,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """Reject a claim request"""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    user_data = get_user_from_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user or db_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    
    claim = get_claim_request_by_id(db, claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim request not found"
        )
    
    if claim.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Claim has already been {claim.status}"
        )
    
    updated_claim = reject_claim_request(
        db=db,
        claim_id=claim_id,
        admin_id=db_user.id,
        admin_notes=request.admin_notes
    )
    
    return {
        "status": "success",
        "message": "Claim rejected.",
        "claim": {
            "id": updated_claim.id,
            "status": updated_claim.status,
            "reviewed_at": updated_claim.reviewed_at.isoformat() if updated_claim.reviewed_at else None,
            "admin_notes": updated_claim.admin_notes
        }
    }


# ==================== LOST ITEMS ADMIN ENDPOINTS ====================

@router.get("/lost-items/pending")
def get_pending_lost_items(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get active lost items (not yet found)"""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    user_data = get_user_from_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user or db_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    
    from app.models.item_model import LostItemDB
    
    active_items = db.query(LostItemDB).filter(
        LostItemDB.status == "active"
    ).offset(skip).limit(limit).all()
    
    return {
        "status": "success",
        "items": [
            {
                "id": item.id,
                "description": item.description,
                "location": item.location,
                "date_lost": item.date_lost.isoformat() if item.date_lost else None,
                "image_url": item.image_url,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None
            }
            for item in active_items
        ]
    }
