from typing import Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderItem


class OrderRepository:
    """Repository for Order model"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID with items"""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product_size))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Order]:
        """Get all orders with pagination"""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .offset(skip)
            .limit(limit)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> list[Order]:
        """Get orders by status"""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.status == status)
            .offset(skip)
            .limit(limit)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_customer_name(
        self, customer_name: str, skip: int = 0, limit: int = 100
    ) -> list[Order]:
        """Get orders by customer name"""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.customer_name.ilike(f"%{customer_name}%"))
            .offset(skip)
            .limit(limit)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, **kwargs) -> Order:
        """Create a new order"""
        order = Order(**kwargs)
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def update(self, order_id: int, **kwargs) -> Optional[Order]:
        """Update order by ID"""
        stmt = (
            update(Order).where(Order.id == order_id).values(**kwargs).returning(Order)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def update_status(self, order_id: int, status: str) -> Optional[Order]:
        """Update order status"""
        return await self.update(order_id, status=status)

    async def delete(self, order_id: int) -> bool:
        """Delete order by ID"""
        stmt = delete(Order).where(Order.id == order_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    # OrderItem methods
    async def get_item_by_id(self, item_id: int) -> Optional[OrderItem]:
        """Get order item by ID"""
        result = await self.session.execute(
            select(OrderItem)
            .options(selectinload(OrderItem.product_size))
            .where(OrderItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def add_item(self, **kwargs) -> OrderItem:
        """Add item to order"""
        item = OrderItem(**kwargs)
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def get_order_total(self, order_id: int) -> float:
        """Calculate total amount for order"""
        result = await self.session.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        items = result.scalars().all()
        return sum(item.price * item.quantity for item in items)
