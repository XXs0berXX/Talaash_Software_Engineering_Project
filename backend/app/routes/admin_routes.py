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
    
    # FIXED: Changed from "pending" to "active" for lost items
    pending_lost_items = db.query(func.count(LostItemDB.id)).filter(LostItemDB.status == "active").scalar()
    total_lost_items = db.query(func.count(LostItemDB.id)).scalar()
    # FIXED: Changed from "approved" to "active"
    approved_lost_items = db.query(func.count(LostItemDB.id)).filter(LostItemDB.status == "active").scalar()
    
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
    """Get active lost items (not yet found) - excludes 'found' status"""
    
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
    
    # FIXED: Changed from "approved" to "active"
    active_items = db.query(LostItemDB).filter(
        LostItemDB.status == "active"  # Changed this line
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

@router.post("/lost-items/{item_id}/approve")
def approve_lost_item(
    item_id: int,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """Approve a lost item report"""
    
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
    
    db_item = db.query(LostItemDB).filter(LostItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lost item not found"
        )
    
    db_item.status = "approved"
    db.commit()
    db.refresh(db_item)
    
    return {
        "status": "success",
        "message": "Lost item approved successfully",
        "item": {
            "id": db_item.id,
            "status": db_item.status
        }
    }


@router.post("/lost-items/{item_id}/reject")
def reject_lost_item(
    item_id: int,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """Reject a lost item report"""
    
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
    
    db_item = db.query(LostItemDB).filter(LostItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lost item not found"
        )
    
    db_item.status = "rejected"
    db.commit()
    db.refresh(db_item)
    
    return {
        "status": "success",
        "message": "Lost item rejected",
        "item": {
            "id": db_item.id,
            "status": db_item.status
        }
    }

#==================== FOUND ITEMS ADMIN ENDPOINTS ====================

@router.get("/items/approved")
def get_approved_found_items(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get approved found items (available for claiming)"""
    
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
    
    # Get approved found items
    approved_items = db.query(FoundItemDB).filter(
        FoundItemDB.status == "approved"
    ).offset(skip).limit(limit).all()
    
    return {
        "status": "success",
        "items": [
            {
                "id": item.id,
                "description": item.description,
                "location": item.location,
                "date_found": item.date_found.isoformat() if item.date_found else None,
                "image_url": item.image_url,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None
            }
            for item in approved_items
        ]
    }


@router.get("/items/pending")
def get_pending_found_items(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get pending found items (waiting for admin approval)"""
    
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
    
    # Get pending found items
    pending_items = db.query(FoundItemDB).filter(
        FoundItemDB.status == "pending"
    ).offset(skip).limit(limit).all()
    
    return {
        "status": "success",
        "items": [
            {
                "id": item.id,
                "description": item.description,
                "location": item.location,
                "date_found": item.date_found.isoformat() if item.date_found else None,
                "image_url": item.image_url,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None
            }
            for item in pending_items
        ]
    }


@router.post("/items/{item_id}/approve")
def approve_found_item(
    item_id: int,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """Approve a found item (makes it visible for claiming)"""
    
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
    
    db_item = db.query(FoundItemDB).filter(FoundItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found item not found"
        )
    
    db_item.status = "approved"
    db.commit()
    db.refresh(db_item)
    
    return {
        "status": "success",
        "message": "Found item approved successfully",
        "item": {
            "id": db_item.id,
            "status": db_item.status
        }
    }


@router.post("/items/{item_id}/reject")
def reject_found_item(
    item_id: int,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """Reject a found item"""
    
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
    
    db_item = db.query(FoundItemDB).filter(FoundItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found item not found"
        )
    
    db_item.status = "rejected"
    db.commit()
    db.refresh(db_item)
    
    return {
        "status": "success",
        "message": "Found item rejected",
        "item": {
            "id": db_item.id,
            "status": db_item.status
        }
    }


@router.post("/items/found/add", status_code=status.HTTP_201_CREATED)
async def admin_add_found_item(
    description: str = Form(...),
    location: str = Form(...),
    date_found: str = Form(...),
    file: UploadFile = File(...),
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """Admin endpoint to add a found item - automatically approved"""
    
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
    
    # Import necessary items
    import uuid
    UPLOAD_DIR = "uploads"
    MAX_FILE_SIZE_MB = 5
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    
    def validate_image_file(filename: str) -> bool:
        _, ext = os.path.splitext(filename)
        return ext.lower() in ALLOWED_EXTENSIONS
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    if not validate_image_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    file_content = await file.read()
    file_size_mb = len(file_content) / (1024 * 1024)
    
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_FILE_SIZE_MB}MB limit"
        )
    
    try:
        date_found_obj = datetime.fromisoformat(date_found)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format: 2024-01-15T14:30:00"
        )
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )
    
    image_url = f"/uploads/{unique_filename}"
    
    # Create found item with approved status (admin added items are auto-approved)
    db_item = FoundItemDB(
        user_id=db_user.id,
        description=description,
        location=location,
        date_found=date_found_obj,
        image_url=image_url,
        status="approved"  # Admin-added items are immediately approved
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    return {
        "status": "success",
        "message": "Found item added successfully and is now available for claiming",
        "item": {
            "id": db_item.id,
            "description": db_item.description,
            "location": db_item.location,
            "date_found": db_item.date_found.isoformat(),
            "image_url": db_item.image_url,
            "status": db_item.status
        }
    }