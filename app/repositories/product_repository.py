from typing import Optional
from uuid import UUID
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.product import Product, ProductSize


class ProductRepository:
    """Repository for Product model"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, product_id: UUID) -> Optional[Product]:
        """Get product by ID with sizes"""
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.sizes))
            .where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Product]:
        """Get product by slug with sizes"""
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.sizes))
            .where(Product.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Product]:
        """Get all products with pagination"""
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.sizes))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_category(
        self, category_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Product]:
        """Get products by category"""
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.sizes))
            .where(Product.category_id == category_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_available(self, skip: int = 0, limit: int = 100) -> list[Product]:
        """Get all available products"""
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.sizes))
            .where(Product.is_available == True)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> list[Product]:
        """Search products by name or description"""
        search_pattern = f"%{query}%"
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.sizes))
            .where(
                (Product.name.ilike(search_pattern))
                | (Product.description.ilike(search_pattern))
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, **kwargs) -> Product:
        """Create a new product"""
        product = Product(**kwargs)
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def update(self, product_id: UUID, **kwargs) -> Optional[Product]:
        """Update product by ID"""
        stmt = (
            update(Product)
            .where(Product.id == product_id)
            .values(**kwargs)
            .returning(Product)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete(self, product_id: UUID) -> bool:
        """Delete product by ID"""
        stmt = delete(Product).where(Product.id == product_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def slug_exists(self, slug: str) -> bool:
        """Check if slug already exists"""
        result = await self.session.execute(
            select(Product.id).where(Product.slug == slug)
        )
        return result.scalar_one_or_none() is not None

    # ProductSize methods
    async def get_size_by_id(self, size_id: int) -> Optional[ProductSize]:
        """Get product size by ID"""
        result = await self.session.execute(
            select(ProductSize).where(ProductSize.id == size_id)
        )
        return result.scalar_one_or_none()

    async def create_size(self, **kwargs) -> ProductSize:
        """Create a new product size"""
        size = ProductSize(**kwargs)
        self.session.add(size)
        await self.session.commit()
        await self.session.refresh(size)
        return size

    async def update_size(self, size_id: int, **kwargs) -> Optional[ProductSize]:
        """Update product size by ID"""
        stmt = (
            update(ProductSize)
            .where(ProductSize.id == size_id)
            .values(**kwargs)
            .returning(ProductSize)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_size(self, size_id: int) -> bool:
        """Delete product size by ID"""
        stmt = delete(ProductSize).where(ProductSize.id == size_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
