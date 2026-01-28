"""
Authentication Service

Password hashing, JWT token generation and validation.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.config import settings
from app.models.user import User


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def generate_user_id() -> str:
        """Generate a unique user ID."""
        return f"user-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt. Truncates to 72 bytes (bcrypt limit)."""
        # bcrypt has a 72-byte limit, truncate if necessary
        password_bytes = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
        return pwd_context.hash(password_bytes)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash. Truncates to 72 bytes (bcrypt limit)."""
        # bcrypt has a 72-byte limit, truncate to match hash_password
        password_bytes = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
        return pwd_context.verify(password_bytes, hashed_password)

    @staticmethod
    def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """Verify a JWT token and return the user_id if valid."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except JWTError:
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """Get a user by Google ID."""
        result = await self.db.execute(
            select(User).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        google_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        user = User(
            id=self.generate_user_id(),
            email=email.lower(),
            hashed_password=self.hash_password(password) if password else None,
            google_id=google_id,
            name=name,
            created_at=datetime.utcnow(),
            is_active=True,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not user.hashed_password:
            return None  # User signed up with OAuth, no password
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def authenticate_google(self, google_token: str) -> Optional[dict]:
        """Verify Google token and return user info."""
        try:
            # Verify the token with Google
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={google_token}"
                )
                if response.status_code != 200:
                    return None

                data = response.json()

                # Verify the token is for our app
                if data.get("aud") != settings.google_client_id:
                    return None

                return {
                    "google_id": data.get("sub"),
                    "email": data.get("email"),
                    "name": data.get("name"),
                    "picture": data.get("picture"),
                }
        except Exception:
            return None

    async def get_or_create_google_user(self, google_info: dict) -> User:
        """Get or create a user from Google OAuth info."""
        # First check if user exists by Google ID
        user = await self.get_user_by_google_id(google_info["google_id"])
        if user:
            return user

        # Check if user exists by email (might have signed up with password)
        user = await self.get_user_by_email(google_info["email"])
        if user:
            # Link Google account to existing user
            user.google_id = google_info["google_id"]
            if not user.name and google_info.get("name"):
                user.name = google_info["name"]
            await self.db.commit()
            await self.db.refresh(user)
            return user

        # Create new user
        return await self.create_user(
            email=google_info["email"],
            google_id=google_info["google_id"],
            name=google_info.get("name"),
        )
