from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate


class UserService:
    """Business logic for users."""

    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: UserRole | None = None,
        only_active: bool = False,
    ) -> list[User]:
        if role is not None:
            return await self.user_repo.get_by_role(role=role, skip=skip, limit=limit)
        if only_active:
            return await self.user_repo.get_active_users(skip=skip, limit=limit)
        return await self.user_repo.get_all(skip=skip, limit=limit)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return await self.user_repo.get_by_id(user_id)

    async def update_profile(self, user_id: UUID, data: UserUpdate) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return user

        updated = await self.user_repo.update(user_id, **update_data)
        if updated is None:
            raise ValueError("User not found")
        return updated

    async def update_user(self, user_id: UUID, **kwargs) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")

        if "email" in kwargs and kwargs["email"] != user.email:
            if await self.user_repo.email_exists(kwargs["email"]):
                raise ValueError("Email already registered")

        if "username" in kwargs and kwargs["username"] != user.username:
            if await self.user_repo.username_exists(kwargs["username"]):
                raise ValueError("Username already taken")

        updated = await self.user_repo.update(user_id, **kwargs)
        if updated is None:
            raise ValueError("User not found")
        return updated

    async def change_user_role(self, user_id: UUID, role: UserRole) -> User:
        updated = await self.user_repo.update(user_id, role=role)
        if updated is None:
            raise ValueError("User not found")
        return updated

    async def deactivate_user(self, user_id: UUID) -> User:
        updated = await self.user_repo.update(user_id, is_active=False)
        if updated is None:
            raise ValueError("User not found")
        return updated

    async def delete_user(self, user_id: UUID) -> None:
        deleted = await self.user_repo.delete(user_id)
        if not deleted:
            raise ValueError("User not found")
