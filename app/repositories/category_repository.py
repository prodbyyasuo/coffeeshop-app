from typing import Optional
from uuid import UUID
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.category import Category


class CategoryRepository:
    """Repository for Category model"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, category_id: UUID) -> Optional[Category]:
        """Get category by ID"""
        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug"""
        result = await self.session.execute(
            select(Category).where(Category.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Category]:
        """Get all categories with pagination"""
        result = await self.session.execute(select(Category).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_active(self, skip: int = 0, limit: int = 100) -> list[Category]:
        """Get all active categories"""
        result = await self.session.execute(
            select(Category).where(Category.is_active == True).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, **kwargs) -> Category:
        """Create a new category"""
        category = Category(**kwargs)
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def update(self, category_id: UUID, **kwargs) -> Optional[Category]:
        """Update category by ID"""
        stmt = (
            update(Category)
            .where(Category.id == category_id)
            .values(**kwargs)
            .returning(Category)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete(self, category_id: UUID) -> bool:
        """Delete category by ID"""
        stmt = delete(Category).where(Category.id == category_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def slug_exists(self, slug: str) -> bool:
        """Check if slug already exists"""
        result = await self.session.execute(
            select(Category.id).where(Category.slug == slug)
        )
        return result.scalar_one_or_none() is not None
