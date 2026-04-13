from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.core.security import verify_password, get_password_hash, create_access_token
from app.schemas.user import UserCreate, UserLogin
from app.schemas.token import Token


class AuthService:
    """Service for authentication operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def register(self, user_data: UserCreate) -> User:
        """Register a new user"""
        # Check if email already exists
        if await self.user_repo.email_exists(user_data.email):
            raise ValueError("Email already registered")

        # Check if username already exists
        if await self.user_repo.username_exists(user_data.username):
            raise ValueError("Username already taken")

        # Hash password
        hashed_password = get_password_hash(user_data.password)

        # Create user
        user = await self.user_repo.create(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            role=UserRole.CUSTOMER,
            is_active=True,
        )

        return user

    async def login(self, login_data: UserLogin) -> Token:
        """Authenticate user and return JWT token"""
        # Get user by email
        user = await self.user_repo.get_by_email(login_data.email)

        if not user:
            raise ValueError("Invalid email or password")

        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            raise ValueError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise ValueError("User account is inactive")

        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value}
        )

        return Token(access_token=access_token, token_type="bearer")

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return await self.user_repo.get_by_id(user_id)

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password"""
        user = await self.user_repo.get_by_email(email)

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user
