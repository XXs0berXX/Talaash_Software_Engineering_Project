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


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_signup(
    request: AdminSignupRequest,
    db: Session = Depends(get_db)
):
    """
    Admin signup endpoint
    
    - Validates admin key
    - Validates @khi.iba.edu.pk email domain
    - Creates admin user record with mobile number
    
    Args:
        request: Admin signup request with name, email, mobile, and admin key
        db: Database session
        
    Returns:
        Created admin user object
        
    Raises:
        HTTPException: If admin key is invalid, email is invalid, or user exists
    """
    
    # Validate admin key
    if request.admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin registration key"
        )
    
    # Validate email domain
    if not validate_iba_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only @khi.iba.edu.pk email addresses are allowed"
        )
    
    # Check if user already exists
    if user_exists(db, request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create admin user with "admin" role
    db_user = create_user(
        db=db,
        name=request.name,
        email=request.email,
        mobile=request.mobile,  # NEW: Include mobile
        role="admin"
    )
    
    return db_user


@router.post("/login")
def admin_login(
    request: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Admin login endpoint
    
    - Validates Firebase token
    - Verifies user is admin
    - Returns admin dashboard redirect
    
    Args:
        request: Login request with email and Firebase token
        db: Database session
        
    Returns:
        Admin information and authentication status
        
    Raises:
        HTTPException: If token invalid, user not found, or not admin
    """
    
    # Validate email domain
    if not validate_iba_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email domain"
        )
    
    # Verify Firebase token
    user_data = get_user_from_token(request.token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Get user from database
    db_user = get_user_by_email(db, request.email)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )
    
    # Verify user is admin
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
    """
    Admin dashboard data endpoint
    Returns statistics and pending items
    
    Headers:
        authorization: "Bearer <token>"
    
    Returns:
        Dashboard statistics and pending items
        
    Raises:
        HTTPException: If token invalid or user not admin
    """
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    # Extract and verify token
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
    
    # Get user and verify admin
    db_user = get_user_by_email(db, user_data.get("email"))
    
    if not db_user or db_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Admin privileges required."
        )
    
    # Import models
    from app.models.item_model import FoundItemDB, LostItemDB
    
    # Get statistics
    pending_items = db.query(func.count(FoundItemDB.id)).filter(FoundItemDB.status == "pending").scalar()
    total_items = db.query(func.count(FoundItemDB.id)).scalar()
    approved_items = db.query(func.count(FoundItemDB.id)).filter(FoundItemDB.status == "approved").scalar()
    rejected_items = db.query(func.count(FoundItemDB.id)).filter(FoundItemDB.status == "rejected").scalar()
    
    pending_lost_items = db.query(func.count(LostItemDB.id)).filter(LostItemDB.status == "pending").scalar()
    total_lost_items = db.query(func.count(LostItemDB.id)).scalar()
    approved_lost_items = db.query(func.count(LostItemDB.id)).filter(LostItemDB.status == "approved").scalar()
    
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
            "pending_lost_items": pending_lost_items or 0,
            "total_lost_items": total_lost_items or 0,
            "approved_lost_items": approved_lost_items or 0
        }
    }



@router.post("/items/found", status_code=status.HTTP_201_CREATED)
async def add_found_item(
    authorization: Annotated[str | None, Header()] = None,
    description: str = Form(...),
    location: str = Form(...),
    date_found: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Admin endpoint to add found items directly"""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    # Extract and verify token
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
    
    # Get user and verify admin
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user or db_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG, PNG, GIF, and WebP images are allowed"
        )
    
    # Validate file size (5MB max)
    file_content = await file.read()
    if len(file_content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must not exceed 5MB"
        )
    
    # Reset file pointer
    await file.seek(0)
    
    # Parse date
    try:
        parsed_date = datetime.fromisoformat(date_found)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
        )
    
    # Import necessary modules
    from app.models.item_model import FoundItemDB
    from app.utils.file_upload import upload_image
    
    try:
        # Upload image and get URL
        image_url = await upload_image(file)
        
        # Create item with approved status
        new_item = FoundItemDB(
            user_id=db_user.id,
            description=description,
            location=location,
            date_found=parsed_date,
            image_url=image_url,
            status="approved"
        )
        
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        return {
            "status": "success",
            "message": "Found item added successfully",
            "item": {
                "id": new_item.id,
                "user_id": new_item.user_id,
                "description": new_item.description,
                "location": new_item.location,
                "date_found": new_item.date_found.isoformat() if new_item.date_found else None,
                "image_url": new_item.image_url,
                "status": new_item.status,
                "created_at": new_item.created_at.isoformat() if new_item.created_at else None
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add item: {str(e)}"
        )


@router.get("/items/pending")
def get_pending_items(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    """Get pending items for admin review"""
    
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
    
    from app.models.item_model import FoundItemDB
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
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "category": getattr(item, 'category', None),
                "reporter_email": getattr(item, 'reporter_email', None)
            }
            for item in pending_items
        ]
    }


@router.get("/items/approved")
def get_approved_items(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    """Get approved items"""
    
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
    
    from app.models.item_model import FoundItemDB
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
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "category": getattr(item, 'category', None),
                "reporter_email": getattr(item, 'reporter_email', None)
            }
            for item in approved_items
        ]
    }


@router.get("/items/rejected")
def get_rejected_items(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    """Get rejected items"""
    
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
    
    from app.models.item_model import FoundItemDB
    rejected_items = db.query(FoundItemDB).filter(
        FoundItemDB.status == "rejected"
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
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "category": getattr(item, 'category', None),
                "reporter_email": getattr(item, 'reporter_email', None)
            }
            for item in rejected_items
        ]
    }


@router.get("/items/all")
def get_all_items(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    """Get all items regardless of status"""
    
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
    
    from app.models.item_model import FoundItemDB
    all_items = db.query(FoundItemDB).offset(skip).limit(limit).all()
    
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
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "category": getattr(item, 'category', None),
                "reporter_email": getattr(item, 'reporter_email', None)
            }
            for item in all_items
        ]
    }


@router.post("/items/{item_id}/approve")
def approve_item(
    item_id: int,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """Approve a found item"""
    
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
    
    from app.models.item_model import FoundItemDB
    db_item = db.query(FoundItemDB).filter(FoundItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    db_item.status = "approved"
    db.commit()
    db.refresh(db_item)
    
    return {
        "status": "success",
        "message": "Item approved successfully"
    }


@router.post("/items/{item_id}/reject")
def reject_item(
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
    
    from app.models.item_model import FoundItemDB
    db_item = db.query(FoundItemDB).filter(FoundItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    db_item.status = "rejected"
    db.commit()
    
    return {
        "status": "success",
        "message": "Item rejected successfully"
    }


# ==================== INCIDENT REPORT ENDPOINTS ====================

@router.post("/items/{item_id}/incident-report")
def update_item_incident_report(
    item_id: int,
    request: IncidentReportRequest,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """
    Update incident report for a claimed item
    """
    
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
    
    from app.models.item_model import update_incident_report
    
    updated_item = update_incident_report(
        db=db,
        item_id=item_id,
        admin_id=db_user.id,
        incident_report=request.incident_report,
        claimed_by_name=request.claimed_by_name,
        claimed_by_email=request.claimed_by_email,
        claimed_by_mobile=request.claimed_by_mobile
    )
    
    if not updated_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return {
        "status": "success",
        "message": "Incident report updated successfully",
        "item": {
            "id": updated_item.id,
            "description": updated_item.description,
            "location": updated_item.location,
            "status": updated_item.status,
            "incident_report": updated_item.incident_report,
            "incident_updated_at": updated_item.incident_updated_at.isoformat() if updated_item.incident_updated_at else None,
            "claimed_by_name": updated_item.claimed_by_name,
            "claimed_by_email": updated_item.claimed_by_email,
            "claimed_by_mobile": updated_item.claimed_by_mobile,
            "claimed_at": updated_item.claimed_at.isoformat() if updated_item.claimed_at else None
        }
    }


@router.get("/items/{item_id}/incident-report")
def get_item_incident_report(
    item_id: int,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """
    Get incident report for an item
    """
    
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
    
    from app.models.item_model import get_found_item_by_id
    
    item = get_found_item_by_id(db, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    updated_by_admin = None
    if item.incident_updated_by:
        admin = get_user_by_id(db, item.incident_updated_by)
        if admin:
            updated_by_admin = {
                "id": admin.id,
                "name": admin.name,
                "email": admin.email
            }
    
    return {
        "status": "success",
        "item": {
            "id": item.id,
            "description": item.description,
            "location": item.location,
            "date_found": item.date_found.isoformat() if item.date_found else None,
            "image_url": item.image_url,
            "status": item.status,
            "incident_report": item.incident_report,
            "incident_updated_at": item.incident_updated_at.isoformat() if item.incident_updated_at else None,
            "incident_updated_by": updated_by_admin,
            "claimed_by_name": item.claimed_by_name,
            "claimed_by_email": item.claimed_by_email,
            "claimed_by_mobile": item.claimed_by_mobile,
            "claimed_at": item.claimed_at.isoformat() if item.claimed_at else None
        }
    }


# ==================== LOST ITEMS ADMIN ENDPOINTS ====================

@router.get("/lost-items/pending")
def get_pending_lost_items(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    """Get pending lost items for admin review"""
    
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