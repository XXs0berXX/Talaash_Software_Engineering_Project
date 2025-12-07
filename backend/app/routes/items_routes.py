"""
Item routes for managing found and lost items
Handles upload, retrieval, and search functionality
"""

import os
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile, Query, Form, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.db import get_db
from app.models.item_model import (
    FoundItemRequest,
    FoundItemResponse,
    FoundItemListResponse,
    LostItemRequest,
    LostItemResponse,
    create_found_item,
    get_found_items,
    get_found_item_by_id,
    get_found_items_by_user,
    create_lost_item,
    get_lost_items,
    FoundItemDB,
    LostItemDB
)
from app.models.user_model import get_user_by_email, get_user_by_id
from app.utils.validators import (
    validate_file_size,
    sanitize_filename,
    validate_required_fields
)
from app.utils.firebase_verify import (
    get_user_from_token,
    initialize_firebase
)

router = APIRouter()
security = HTTPBearer()

# Configuration
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE_MB = 5
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

initialize_firebase()


# ============ PYDANTIC MODELS ============

class ClaimItemRequest(BaseModel):
    """Request body for claiming an item"""
    name: str
    email: str
    mobile: str
    notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@khi.iba.edu.pk",
                "mobile": "03001234567",
                "notes": "This is my blue backpack. It has my student ID inside."
            }
        }


# ============ HELPER FUNCTIONS ============

def validate_image_file(filename: str) -> bool:
    """Validate image file extension"""
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS


# ============ FOUND ITEMS ENDPOINTS ============

@router.post("/found", response_model=FoundItemResponse, status_code=status.HTTP_201_CREATED)
async def upload_found_item(
    description: str = Form(...),
    location: str = Form(...),
    date_found: str = Form(...),
    file: UploadFile = File(...),
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Upload a found item with image"""
    
    token_str = token.credentials
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token provided."
        )
    
    user_data = get_user_from_token(token_str)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )
    
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
    await file.seek(0)
    
    if not validate_file_size(len(file_content), MAX_FILE_SIZE_MB):
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
    
    db_item = create_found_item(
        db=db,
        user_id=db_user.id,
        description=description,
        location=location,
        date_found=date_found_obj,
        image_url=image_url
    )
    
    return db_item


@router.get("/found", response_model=FoundItemListResponse)
def get_found_items_list(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    status_filter: str = Query("approved", regex="^(pending|approved|claimed|all)$")
):
    """Get list of found items"""
    
    query = db.query(FoundItemDB)
    
    if status_filter != "all":
        query = query.filter(FoundItemDB.status == status_filter)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return FoundItemListResponse(
        items=items,
        total=total
    )


@router.get("/found/my-items", response_model=FoundItemListResponse)
def get_my_found_items(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get all found items reported by the current authenticated user"""
    
    token_str = token.credentials
    user_data = get_user_from_token(token_str)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )
    
    items = db.query(FoundItemDB).filter(FoundItemDB.user_id == db_user.id).all()
    
    return FoundItemListResponse(
        items=items,
        total=len(items)
    )


@router.get("/found/{item_id}", response_model=FoundItemResponse)
def get_found_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    """Get details of a specific found item"""
    
    db_item = get_found_item_by_id(db, item_id)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found item not found"
        )
    
    return db_item

@router.post("/found/{item_id}/claim")
def claim_found_item(
    item_id: int,
    request: ClaimItemRequest,
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Submit a claim request for a found item
    Creates a pending claim that requires admin approval
    Item remains visible to other users until admin approves a claim
    """
    
    token_str = token.credentials
    user_data = get_user_from_token(token_str)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db_item = get_found_item_by_id(db, item_id)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Check item status
    if db_item.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This item cannot be claimed. Current status: {db_item.status}"
        )
    
    # Prevent self-claiming
    if db_item.user_id == db_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot claim an item you reported"
        )
    
    # Check if user already has a pending claim for this item
    from app.models.claim_request_model import has_user_claimed_item, create_claim_request
    
    if has_user_claimed_item(db, db_user.id, item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a claim for this item. Please wait for admin review."
        )
    
    # Create claim request
    claim_request = create_claim_request(
        db=db,
        item_id=item_id,
        user_id=db_user.id,
        claimant_name=request.name,
        claimant_email=request.email,
        claimant_mobile=request.mobile,
        notes=request.notes
    )
    
    return {
        "status": "success",
        "message": "Claim request submitted successfully! An admin will review your request. The item will remain available until your claim is approved.",
        "claim_request": {
            "id": claim_request.id,
            "item_id": claim_request.item_id,
            "status": claim_request.status,
            "created_at": claim_request.created_at.isoformat()
        }
    }



# endpoint to get user's claim requests
@router.get("/claims/my-claims")
def get_my_claims(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get all claim requests submitted by the current user"""
    
    token_str = token.credentials
    user_data = get_user_from_token(token_str)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    from app.models.claim_request_model import get_user_claim_requests, ClaimRequestDB
    from app.models.item_model import FoundItemDB
    
    claims = get_user_claim_requests(db, db_user.id)
    
    # Enrich with item details
    result = []
    for claim in claims:
        item = db.query(FoundItemDB).filter(FoundItemDB.id == claim.item_id).first()
        if item:
            result.append({
                "claim_id": claim.id,
                "status": claim.status,
                "created_at": claim.created_at.isoformat(),
                "reviewed_at": claim.reviewed_at.isoformat() if claim.reviewed_at else None,
                "admin_notes": claim.admin_notes,
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

@router.get("/found/user/{user_id}")
def get_user_found_items(
    user_id: int,
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get all found items reported by a specific user"""
    
    token_str = token.credentials
    user_data = get_user_from_token(token_str)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    items = get_found_items_by_user(db, user_id)
    
    return {
        "status": "success",
        "items": items,
        "total": len(items)
    }


@router.delete("/found/{item_id}")
def delete_found_item(
    item_id: int,
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Delete a found item (only owner can delete)"""
    
    token_str = token.credentials
    user_data = get_user_from_token(token_str)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db_item = get_found_item_by_id(db, item_id)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    if db_item.user_id != db_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own items"
        )
    
    if db_item.image_url:
        file_path = db_item.image_url.lstrip('/')
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete file: {e}")
    
    db.delete(db_item)
    db.commit()
    
    return {"status": "success", "message": "Item deleted successfully"}


# ============ LOST ITEMS ENDPOINTS ============

@router.post("/lost", response_model=LostItemResponse, status_code=status.HTTP_201_CREATED)
async def upload_lost_item(
    description: str = Form(...),
    location: str = Form(...),
    date_lost: str = Form(...),
    file: UploadFile = File(...),
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Upload a lost item with image - automatically approved"""
    
    token_str = token.credentials
    user_data = get_user_from_token(token_str)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )
    
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
    await file.seek(0)
    if not validate_file_size(len(file_content), MAX_FILE_SIZE_MB):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_FILE_SIZE_MB}MB limit"
        )
    
    try:
        date_lost_obj = datetime.fromisoformat(date_lost)
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
    
    # Create lost item with active status (auto-approved)
    db_item = LostItemDB(
        user_id=db_user.id,
        description=description,
        location=location,
        date_lost=date_lost_obj,
        image_url=image_url,
        status="active"  # Lost items are active (visible) by default
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    return db_item


@router.get("/lost")
def get_lost_items_list(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    status_filter: str = Query("approved", regex="^(approved|found|all)$")
):
    """Get list of lost items"""
    
    query = db.query(LostItemDB)
    
    if status_filter != "all":
        query = query.filter(LostItemDB.status == status_filter)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return {
        "items": items,
        "total": total
    }


@router.get("/lost/my-items")
def get_my_lost_items(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get all lost items reported by the current authenticated user"""
    
    token_str = token.credentials
    user_data = get_user_from_token(token_str)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )
    
    items = db.query(LostItemDB).filter(LostItemDB.user_id == db_user.id).all()
    
    return {
        "items": items,
        "total": len(items)
    }


@router.post("/lost/{item_id}/mark-found")
def mark_lost_item_as_found(
    item_id: int,
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Mark a lost item as found (only owner can mark)"""
    
    token_str = token.credentials
    user_data = get_user_from_token(token_str)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db_item = db.query(LostItemDB).filter(LostItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    if db_item.user_id != db_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only mark your own items as found"
        )
    
    # Update status and timestamp
    db_item.status = "found"
    db_item.found_at = datetime.utcnow()
    db.commit()
    db.refresh(db_item)
    
    return {
        "status": "success",
        "message": "Item marked as found successfully!",
        "item": {
            "id": db_item.id,
            "status": db_item.status,
            "found_at": db_item.found_at.isoformat() if db_item.found_at else None
        }
    }


@router.delete("/lost/{item_id}")
def delete_lost_item(
    item_id: int,
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Delete a lost item (only owner can delete)"""
    
    token_str = token.credentials
    user_data = get_user_from_token(token_str)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db_item = db.query(LostItemDB).filter(LostItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    if db_item.user_id != db_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own items"
        )
    
    if db_item.image_url:
        file_path = db_item.image_url.lstrip('/')
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete file: {e}")
    
    db.delete(db_item)
    db.commit()
    
    return {"status": "success", "message": "Item deleted successfully"}