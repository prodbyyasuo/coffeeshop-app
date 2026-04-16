from typing import Optional
from uuid import UUID
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.cart import Cart, CartItem
from app.models.product import ProductSize


class CartRepository:
    """Repository for Cart model"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, cart_id: UUID) -> Optional[Cart]:
        """Get cart by ID with items"""
        result = await self.session.execute(
            select(Cart)
            .options(
                selectinload(Cart.items)
                .selectinload(CartItem.product_size)
                .selectinload(ProductSize.product)
            )
            .where(Cart.id == cart_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> Optional[Cart]:
        """Get cart by user ID with items"""
        result = await self.session.execute(
            select(Cart)
            .options(
                selectinload(Cart.items)
                .selectinload(CartItem.product_size)
                .selectinload(ProductSize.product)
            )
            .where(Cart.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: UUID) -> Cart:
        """Create a new cart for user"""
        cart = Cart(user_id=user_id)
        self.session.add(cart)
        await self.session.commit()
        await self.session.refresh(cart)
        return cart

    async def delete(self, cart_id: UUID) -> bool:
        """Delete cart by ID"""
        stmt = delete(Cart).where(Cart.id == cart_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def clear_cart(self, cart_id: UUID) -> bool:
        """Clear all items from cart"""
        stmt = delete(CartItem).where(CartItem.cart_id == cart_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    # CartItem methods
    async def get_item_by_id(self, item_id: int) -> Optional[CartItem]:
        """Get cart item by ID"""
        result = await self.session.execute(
            select(CartItem)
            .options(
                selectinload(CartItem.product_size).selectinload(ProductSize.product)
            )
            .where(CartItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_item_by_product_size(
        self, cart_id: UUID, product_size_id: int
    ) -> Optional[CartItem]:
        """Get cart item by cart_id and product_size_id"""
        result = await self.session.execute(
            select(CartItem).where(
                (CartItem.cart_id == cart_id)
                & (CartItem.product_size_id == product_size_id)
            )
        )
        return result.scalar_one_or_none()

    async def add_item(self, **kwargs) -> CartItem:
        """Add item to cart"""
        item = CartItem(**kwargs)
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def update_item(self, item_id: int, **kwargs) -> Optional[CartItem]:
        """Update cart item by ID"""
        stmt = (
            update(CartItem)
            .where(CartItem.id == item_id)
            .values(**kwargs)
            .returning(CartItem)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_item(self, item_id: int) -> bool:
        """Delete cart item by ID"""
        stmt = delete(CartItem).where(CartItem.id == item_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_cart_total(self, cart_id: UUID) -> float:
        """Calculate total amount for cart"""
        result = await self.session.execute(
            select(CartItem).where(CartItem.cart_id == cart_id)
        )
        items = result.scalars().all()
        return sum(item.price * item.quantity for item in items)
