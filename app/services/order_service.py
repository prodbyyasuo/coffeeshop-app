from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderCreate


class OrderService:
    """Business logic for orders."""

    def __init__(self, session: AsyncSession):
        self.order_repo = OrderRepository(session)
        self.cart_repo = CartRepository(session)

    async def list_orders(
        self,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        customer_name: str | None = None,
        user_id: UUID | None = None,
    ) -> list[Order]:
        if user_id is not None:
            return await self.order_repo.get_by_user_id(
                user_id=user_id,
                skip=skip,
                limit=limit,
                status=status,
            )
        if status:
            return await self.order_repo.get_by_status(
                status=status, skip=skip, limit=limit
            )
        if customer_name:
            return await self.order_repo.get_by_customer_name(
                customer_name=customer_name,
                skip=skip,
                limit=limit,
            )
        return await self.order_repo.get_all(skip=skip, limit=limit)

    async def get_order_by_id(self, order_id: int) -> Order:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise ValueError("Order not found")
        return order

    async def create_from_cart(self, user_id: UUID, data: OrderCreate) -> Order:
        cart = await self.cart_repo.get_by_user_id(user_id)
        if cart is None or not cart.items:
            raise ValueError("Cart is empty")

        total_amount = Decimal("0.00")
        for cart_item in cart.items:
            total_amount += Decimal(cart_item.price) * cart_item.quantity

        order = await self.order_repo.create(
            user_id=user_id,
            customer_name=data.customer_name,
            ready_time=data.ready_time,
            total_amount=total_amount.quantize(Decimal("0.01")),
            status="pending",
        )

        for cart_item in cart.items:
            await self.order_repo.add_item(
                order_id=order.id,
                product_size_id=cart_item.product_size_id,
                quantity=cart_item.quantity,
                price=cart_item.price,
            )

        await self.cart_repo.clear_cart(cart.id)

        created_order = await self.order_repo.get_by_id(order.id)
        if created_order is None:
            raise ValueError("Order not found")
        return created_order

    async def update_status(self, order_id: int, status: str) -> Order:
        updated = await self.order_repo.update_status(order_id=order_id, status=status)
        if updated is None:
            raise ValueError("Order not found")

        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise ValueError("Order not found")
        return order

    async def cancel_order(self, order_id: int) -> None:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise ValueError("Order not found")

        if order.status not in {"pending", "processing"}:
            raise ValueError("Order cannot be cancelled in current status")

        await self.order_repo.update_status(order_id=order_id, status="cancelled")
