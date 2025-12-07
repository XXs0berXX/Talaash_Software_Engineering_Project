"""
Authentication routes for user signup and login
Handles Firebase authentication integration
Now includes mobile number support
"""
import os
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import Annotated
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user_model import (
    UserSignupRequest,
    UserResponse,
    create_user,
    get_user_by_email,
    user_exists
)
from app.utils.validators import validate_iba_email
from app.utils.firebase_verify import (
    extract_token_from_header,
    get_user_from_token,
    initialize_firebase
)

router = APIRouter()

# Debug: Print environment variable
print("=" * 50)
print("🔍 DEBUG: Checking Firebase configuration...")
firebase_config_path = os.getenv("FIREBASE_CONFIG_PATH")
print(f"FIREBASE_CONFIG_PATH: {firebase_config_path}")
if firebase_config_path:
    abs_path = os.path.abspath(firebase_config_path)
    print(f"Absolute path: {abs_path}")
    print(f"File exists: {os.path.exists(firebase_config_path)}")
    if os.path.exists(firebase_config_path):
        print(f"File size: {os.path.getsize(firebase_config_path)} bytes")
else:
    print("❌ FIREBASE_CONFIG_PATH is not set!")
print("=" * 50)

# Initialize Firebase on startup
try:
    initialize_firebase()
    print("✅ Firebase initialization completed")
except Exception as e:
    print(f"❌ Firebase initialization failed: {e}")


class LoginRequest(BaseModel): 
    """Pydantic Model for login request body"""
    email: str
    token: str


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    request: UserSignupRequest,
    db: Session = Depends(get_db)
):
    """
    User signup endpoint
    
    - Validates that email ends with @khi.iba.edu.pk
    - Validates mobile number format
    - Creates user record in database
    - Frontend handles Firebase Authentication
    
    Args:
        request: Signup request with name, email, and mobile
        db: Database session
        
    Returns:
        Created user object
        
    Raises:
        HTTPException: If email is invalid, mobile is invalid, or user already exists
    """
    
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
    
    # Create user with default "user" role and mobile number
    db_user = create_user(
        db=db,
        name=request.name,
        email=request.email,
        mobile=request.mobile,  # NEW: Include mobile number
        role="user"
    )
    
    return db_user


@router.post("/login")
def login(
    request: LoginRequest, 
    db: Session = Depends(get_db)
):
    """
    User login endpoint
    
    - Validates Firebase token
    - Returns user information including mobile number
    - Frontend handles Firebase Authentication, backend validates token
    
    Args:
        request: JSON body containing email and Firebase ID token
        db: Database session
        
    Returns:
        User information and authentication status
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Debug logging
    print("\n" + "=" * 50)
    print("🔐 LOGIN REQUEST RECEIVED")
    print(f"Email: {request.email}")
    print(f"Token (first 50 chars): {request.token[:50]}...")
    print("=" * 50)
    
    # Validate email domain
    if not validate_iba_email(request.email):
        print("❌ Email validation failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email domain"
        )
    
    print("✅ Email validation passed")
    
    # Verify Firebase token
    print("🔍 Verifying Firebase token...")
    try:
        user_data = get_user_from_token(request.token)
        print(f"Token verification result: {user_data}")
    except Exception as e:
        print(f"❌ Token verification exception: {e}")
        raise
    
    if not user_data:
        print("❌ Token verification returned None")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    print("✅ Token verified successfully")
    print(f"User data from token: {user_data}")
    
    # Get user from database
    print(f"🔍 Looking up user in database: {request.email}")
    db_user = get_user_by_email(db, request.email)
    if not db_user:
        print("❌ User not found in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please sign up first."
        )
    
    print("✅ User found in database")
    print(f"User ID: {db_user.id}, Role: {db_user.role}")
    
    response = {
        "status": "success",
        "user": {
            "id": db_user.id,
            "name": db_user.name,
            "email": db_user.email,
            "mobile": db_user.mobile,  # NEW: Include mobile in response
            "role": db_user.role
        },
        "token": request.token
    }
    
    print("✅ Login successful")
    print("=" * 50 + "\n")
    
    return response


@router.get("/verify-token")
def verify_token(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """
    Verify Firebase token validity
    
    Headers:
        authorization: "Bearer <token>"
    
    Returns:
        Token validity status and user information including mobile
        
    Raises:
        HTTPException: If token is invalid
    """
    
    # Check if header is present
    if not authorization:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    # Extract token from header
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    # Verify token
    user_data = get_user_from_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Get user from database
    db_user = get_user_by_email(db, user_data.get("email"))
    if not db_user:
        # User is authenticated via Firebase but not in local DB
        return {
            "status": "needs_signup",
            "email": user_data.get("email"),
            "message": "User needs to complete signup"
        }
    
    return {
        "status": "valid",
        "user": {
            "id": db_user.id,
            "name": db_user.name,
            "email": db_user.email,
            "mobile": db_user.mobile,  # NEW: Include mobile in response
            "role": db_user.role
        }
    }


@router.post("/logout")
def logout():
    """
    User logout endpoint
    Note: Firebase handles token invalidation on client side
    
    Returns:
        Logout status
    """
    return {
        "status": "success",
        "message": "Logged out successfully. Clear your frontend token."
    }