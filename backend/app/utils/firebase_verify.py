"""
Firebase token verification utilities
Handles JWT token validation and user authentication
"""

import os
from typing import Optional, Dict
import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin import exceptions
from fastapi import HTTPException, status


def initialize_firebase():
    """
    Initialize Firebase Admin SDK
    Ensure FIREBASE_CONFIG_PATH environment variable points to credentials JSON
    """
    try:
        if not firebase_admin._apps:
            config_path = os.getenv("FIREBASE_CONFIG_PATH")
            
            if not config_path:
                raise ValueError(
                    "FIREBASE_CONFIG_PATH environment variable is not set. "
                    "Please set it to the path of your Firebase service account JSON file."
                )
            
            if not os.path.exists(config_path):
                raise FileNotFoundError(
                    f"Firebase credentials file not found at: {config_path}"
                )
            
            # Initialize with credentials
            cred = credentials.Certificate(config_path)
            firebase_admin.initialize_app(cred)
            print(f"✅ Firebase initialized successfully with credentials from: {config_path}")
            
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ Firebase initialization error: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected Firebase initialization error: {e}")
        raise


def verify_token(token: str) -> Optional[Dict]:
    """
    Verify Firebase JWT token and extract user claims
    
    Args:
        token: Firebase ID token
        
    Returns:
        Dict with user claims if valid
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        print(f"🔍 Attempting to verify token...")
        print(f"Token length: {len(token)}")
        print(f"Token preview: {token[:100]}...")
        
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        
        print(f"✅ Token decoded successfully!")
        print(f"Decoded token keys: {decoded_token.keys()}")
        
        return decoded_token
        
    except auth.ExpiredIdTokenError as e:
        print(f"❌ Token expired: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again."
        )
        
    except auth.InvalidIdTokenError as e:
        print(f"❌ Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token. Please login again."
        )
        
    except auth.RevokedIdTokenError as e:
        print(f"❌ Token revoked: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please login again."
        )
        
    except exceptions.FirebaseError as e:
        print(f"❌ Firebase error during token verification: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )
        
    except Exception as e:
        print(f"❌ Unexpected error during token verification: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error during authentication: {str(e)}"
        )


def get_user_from_token(token: str) -> Optional[Dict]:
    """
    Extract user information from verified token
    
    Args:
        token: Firebase ID token
        
    Returns:
        Dict containing user email, uid, and other claims, or None if verification fails
    """
    try:
        print("📝 get_user_from_token called")
        decoded_token = verify_token(token)
        
        if not decoded_token:
            print("⚠️ verify_token returned None")
            return None
        
        user_info = {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "email_verified": decoded_token.get("email_verified", False)
        }
        
        print(f"✅ User info extracted: {user_info}")
        return user_info
        
    except HTTPException as e:
        print(f"⚠️ HTTPException caught in get_user_from_token: {e.detail}")
        # Don't re-raise, just return None so the router can handle it
        return None
        
    except Exception as e:
        print(f"❌ Unexpected error in get_user_from_token: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_token_from_header(authorization_header: Optional[str]) -> Optional[str]:
    """
    Extract token from Authorization header
    Expected format: "Bearer <token>"
    
    Args:
        authorization_header: Authorization header value
        
    Returns:
        Token string if valid format, None otherwise
    """
    if not authorization_header:
        return None
    
    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]