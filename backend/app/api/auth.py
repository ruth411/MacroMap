"""
Authentication API Router

Endpoints for user registration, login, OAuth, and logout.
Sets JWT in httpOnly cookies for security.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limit import limiter
from app.core.config import settings
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
    user: UserResponse


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set the JWT as an httpOnly cookie on the response."""
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,  # JavaScript cannot access this cookie
        secure=settings.effective_cookie_secure,  # HTTPS only; required for SameSite=None
        samesite=settings.effective_cookie_samesite,  # "none" for cross-origin, "lax" for localhost
        max_age=settings.cookie_max_age,
        path="/",  # Cookie sent for all paths
        domain=settings.cookie_domain or None,  # None = auto
    )


def _clear_auth_cookie(response: Response) -> None:
    """Remove the auth cookie from the response."""
    response.delete_cookie(
        key=settings.cookie_name,
        httponly=True,
        secure=settings.effective_cookie_secure,
        samesite=settings.effective_cookie_samesite,
        path="/",
        domain=settings.cookie_domain or None,
    )


@router.post("/register", response_model=AuthResponse)
@limiter.limit(settings.rate_limit_auth)
async def register(
    register_data: RegisterRequest,
    request: Request,  # Required for rate limiter (must be named 'request')
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register a new user with email and password."""
    try:
        logger.info(f"Registration attempt for email: {register_data.email}")
        auth_service = AuthService(db)

        # Check if email already exists
        existing_user = await auth_service.get_user_by_email(register_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Validate password
        if len(register_data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters",
            )

        # Create user
        logger.info("Creating user...")
        user = await auth_service.create_user(
            email=register_data.email,
            password=register_data.password,
            name=register_data.name,
        )
        logger.info(f"User created with id: {user.id}")

        # Generate token and set as httpOnly cookie
        access_token = AuthService.create_access_token(user.id)
        _set_auth_cookie(response, access_token)

        return AuthResponse(
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
@limiter.limit(settings.rate_limit_auth)
async def login(
    login_data: LoginRequest,
    request: Request,  # Required for rate limiter (must be named 'request')
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Login with email and password."""
    auth_service = AuthService(db)

    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Generate token and set as httpOnly cookie
    access_token = AuthService.create_access_token(user.id)
    _set_auth_cookie(response, access_token)

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
        ),
    )


@router.post("/google", response_model=AuthResponse)
@limiter.limit(settings.rate_limit_auth)
async def google_auth(
    google_data: GoogleAuthRequest,
    request: Request,  # Required for rate limiter (must be named 'request')
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate with Google OAuth."""
    auth_service = AuthService(db)

    # Verify Google token
    google_info = await auth_service.authenticate_google(google_data.token)
    if not google_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    # Get or create user
    user = await auth_service.get_or_create_google_user(google_info)

    # Generate token and set as httpOnly cookie
    access_token = AuthService.create_access_token(user.id)
    _set_auth_cookie(response, access_token)

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
        ),
    )


@router.post("/logout")
async def logout(response: Response):
    """Logout by clearing the auth cookie."""
    _clear_auth_cookie(response)
    return {"status": "ok", "message": "Logged out successfully"}


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
