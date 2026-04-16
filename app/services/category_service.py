from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    """Business logic for categories."""

    def __init__(self, session: AsyncSession):
        self.category_repo = CategoryRepository(session)

    async def list_categories(
        self,
        skip: int = 0,
        limit: int = 100,
        only_active: bool = False,
    ) -> list[Category]:
        if only_active:
            return await self.category_repo.get_active(skip=skip, limit=limit)
        return await self.category_repo.get_all(skip=skip, limit=limit)

    async def get_category_by_id(self, category_id: UUID) -> Optional[Category]:
        return await self.category_repo.get_by_id(category_id)

    async def create_category(self, data: CategoryCreate) -> Category:
        if await self.category_repo.slug_exists(data.slug):
            raise ValueError("Category slug already exists")
        return await self.category_repo.create(**data.model_dump())

    async def update_category(
        self,
        category_id: UUID,
        data: CategoryUpdate,
    ) -> Category:
        category = await self.category_repo.get_by_id(category_id)
        if category is None:
            raise ValueError("Category not found")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return category

        new_slug = update_data.get("slug")
        if new_slug and new_slug != category.slug:
            if await self.category_repo.slug_exists(new_slug):
                raise ValueError("Category slug already exists")

        updated = await self.category_repo.update(category_id, **update_data)
        if updated is None:
            raise ValueError("Category not found")
        return updated

    async def delete_category(self, category_id: UUID) -> None:
        deleted = await self.category_repo.delete(category_id)
        if not deleted:
            raise ValueError("Category not found")
