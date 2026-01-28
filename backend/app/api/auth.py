"""
Authentication API Router

Endpoints for user registration, login, and OAuth.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/register", response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register a new user with email and password."""
    try:
        logger.info(f"Registration attempt for email: {request.email}")
        auth_service = AuthService(db)

        # Check if email already exists
        existing_user = await auth_service.get_user_by_email(request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Validate password
        if len(request.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters",
            )

        # Create user
        logger.info("Creating user...")
        user = await auth_service.create_user(
            email=request.email,
            password=request.password,
            name=request.name,
        )
        logger.info(f"User created with id: {user.id}")

        # Generate token
        access_token = AuthService.create_access_token(user.id)
        logger.info("Token generated successfully")

        return AuthResponse(
            access_token=access_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Login with email and password."""
    auth_service = AuthService(db)

    user = await auth_service.authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = AuthService.create_access_token(user.id)

    return AuthResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
        ),
    )


@router.post("/google", response_model=AuthResponse)
async def google_auth(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate with Google OAuth."""
    auth_service = AuthService(db)

    # Verify Google token
    google_info = await auth_service.authenticate_google(request.token)
    if not google_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    # Get or create user
    user = await auth_service.get_or_create_google_user(google_info)

    access_token = AuthService.create_access_token(user.id)

    return AuthResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
    )


@router.get("/debug/hash-test")
async def debug_hash_test():
    """Debug endpoint to test password hashing."""
    import hashlib
    import base64
    from passlib.context import CryptContext

    # Create a fresh CryptContext for testing
    test_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    result = {}

    # Test 1: Simple 10-char password
    try:
        simple_hash = test_ctx.hash("simple1234")
        result["simple_10char"] = "SUCCESS"
    except Exception as e:
        result["simple_10char_error"] = str(e)

    # Test 2: 44-char password (like our base64)
    try:
        b64_test = "KBZZeIjkoNOja4K4MxarMmgOuPAPjNO5BNaBJG0oWg4="
        hash_44 = test_ctx.hash(b64_test)
        result["base64_44char"] = "SUCCESS"
    except Exception as e:
        result["base64_44char_error"] = str(e)

    # Test 3: 72-char password (exact limit)
    try:
        pw_72 = "a" * 72
        hash_72 = test_ctx.hash(pw_72)
        result["exact_72char"] = "SUCCESS"
    except Exception as e:
        result["exact_72char_error"] = str(e)

    # Test 4: 73-char password (over limit)
    try:
        pw_73 = "a" * 73
        hash_73 = test_ctx.hash(pw_73)
        result["over_73char"] = "SUCCESS"
    except Exception as e:
        result["over_73char_error"] = str(e)

    # Test 5: Check passlib version
    import passlib
    result["passlib_version"] = passlib.__version__

    return result
