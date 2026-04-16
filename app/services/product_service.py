from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductSize
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import (
    ProductCreate,
    ProductSizeCreate,
    ProductSizeUpdate,
    ProductUpdate,
)


class ProductService:
    """Business logic for products and product sizes."""

    def __init__(self, session: AsyncSession):
        self.product_repo = ProductRepository(session)
        self.category_repo = CategoryRepository(session)

    async def list_products(
        self,
        category_id: UUID | None = None,
        is_available: bool | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> list[Product]:
        page = max(page, 1)
        size = min(max(size, 1), 100)
        skip = (page - 1) * size

        if search:
            products = await self.product_repo.search(search, skip=skip, limit=size)
        elif category_id:
            products = await self.product_repo.get_by_category(
                category_id,
                skip=skip,
                limit=size,
            )
        elif is_available is True:
            products = await self.product_repo.get_available(skip=skip, limit=size)
        else:
            products = await self.product_repo.get_all(skip=skip, limit=size)

        if is_available is False:
            products = [product for product in products if not product.is_available]

        if min_price is not None:
            products = [
                product
                for product in products
                if any(Decimal(size.price) >= min_price for size in product.sizes)
            ]

        if max_price is not None:
            products = [
                product
                for product in products
                if any(Decimal(size.price) <= max_price for size in product.sizes)
            ]

        return products

    async def get_product_by_id(self, product_id: UUID) -> Optional[Product]:
        return await self.product_repo.get_by_id(product_id)

    async def get_product_by_slug(self, slug: str) -> Optional[Product]:
        return await self.product_repo.get_by_slug(slug)

    async def create_product(self, data: ProductCreate) -> Product:
        category = await self.category_repo.get_by_id(data.category_id)
        if category is None:
            raise ValueError("Category not found")

        if await self.product_repo.slug_exists(data.slug):
            raise ValueError("Product slug already exists")

        payload = data.model_dump(exclude={"sizes"})
        product = await self.product_repo.create(**payload)

        for size in data.sizes:
            await self.product_repo.create_size(
                product_id=product.id,
                size=size.size,
                price=size.price,
                is_available=size.is_available,
            )

        product_with_sizes = await self.product_repo.get_by_id(product.id)
        if product_with_sizes is None:
            raise ValueError("Product not found")
        return product_with_sizes

    async def update_product(self, product_id: UUID, data: ProductUpdate) -> Product:
        product = await self.product_repo.get_by_id(product_id)
        if product is None:
            raise ValueError("Product not found")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return product

        new_slug = update_data.get("slug")
        if new_slug and new_slug != product.slug:
            if await self.product_repo.slug_exists(new_slug):
                raise ValueError("Product slug already exists")

        new_category = update_data.get("category_id")
        if new_category:
            category = await self.category_repo.get_by_id(new_category)
            if category is None:
                raise ValueError("Category not found")

        updated = await self.product_repo.update(product_id, **update_data)
        if updated is None:
            raise ValueError("Product not found")

        product_with_sizes = await self.product_repo.get_by_id(updated.id)
        if product_with_sizes is None:
            raise ValueError("Product not found")
        return product_with_sizes

    async def delete_product(self, product_id: UUID) -> None:
        deleted = await self.product_repo.delete(product_id)
        if not deleted:
            raise ValueError("Product not found")

    async def set_product_availability(
        self, product_id: UUID, is_available: bool
    ) -> Product:
        updated = await self.product_repo.update(product_id, is_available=is_available)
        if updated is None:
            raise ValueError("Product not found")

        product = await self.product_repo.get_by_id(updated.id)
        if product is None:
            raise ValueError("Product not found")
        return product

    async def create_product_size(
        self, product_id: UUID, data: ProductSizeCreate
    ) -> ProductSize:
        product = await self.product_repo.get_by_id(product_id)
        if product is None:
            raise ValueError("Product not found")
        return await self.product_repo.create_size(
            product_id=product_id, **data.model_dump()
        )

    async def update_product_size(
        self, size_id: int, data: ProductSizeUpdate
    ) -> ProductSize:
        size = await self.product_repo.get_size_by_id(size_id)
        if size is None:
            raise ValueError("Product size not found")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return size

        updated = await self.product_repo.update_size(size_id, **update_data)
        if updated is None:
            raise ValueError("Product size not found")
        return updated

    async def delete_product_size(self, size_id: int) -> None:
        deleted = await self.product_repo.delete_size(size_id)
        if not deleted:
            raise ValueError("Product size not found")
