from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart, CartItem
from app.repositories.cart_repository import CartRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.cart import CartItemCreate


class CartService:
    """Business logic for cart operations."""

    def __init__(self, session: AsyncSession):
        self.cart_repo = CartRepository(session)
        self.product_repo = ProductRepository(session)

    async def get_or_create_cart(self, user_id: UUID) -> Cart:
        cart = await self.cart_repo.get_by_user_id(user_id)
        if cart is None:
            cart = await self.cart_repo.create(user_id=user_id)
            cart = await self.cart_repo.get_by_id(cart.id)

        if cart is None:
            raise ValueError("Cart not found")
        return cart

    async def get_user_cart(self, user_id: UUID) -> Cart:
        return await self.get_or_create_cart(user_id)

    async def add_item(self, user_id: UUID, data: CartItemCreate) -> Cart:
        cart = await self.get_or_create_cart(user_id)

        product_size = await self.product_repo.get_size_by_id(data.product_size_id)
        if product_size is None:
            raise ValueError("Product size not found")

        if not product_size.is_available:
            raise ValueError("Product size is not available")

        existing_item = await self.cart_repo.get_item_by_product_size(
            cart.id,
            data.product_size_id,
        )

        if existing_item:
            await self.cart_repo.update_item(
                existing_item.id,
                quantity=existing_item.quantity + data.quantity,
            )
        else:
            await self.cart_repo.add_item(
                cart_id=cart.id,
                product_size_id=data.product_size_id,
                quantity=data.quantity,
                price=product_size.price,
            )

        updated_cart = await self.cart_repo.get_by_id(cart.id)
        if updated_cart is None:
            raise ValueError("Cart not found")
        return updated_cart

    async def update_item_quantity(
        self,
        user_id: UUID,
        item_id: int,
        quantity: int,
    ) -> Cart:
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")

        cart = await self.get_or_create_cart(user_id)
        item = await self.cart_repo.get_item_by_id(item_id)
        if item is None or item.cart_id != cart.id:
            raise ValueError("Cart item not found")

        await self.cart_repo.update_item(item_id, quantity=quantity)
        updated_cart = await self.cart_repo.get_by_id(cart.id)
        if updated_cart is None:
            raise ValueError("Cart not found")
        return updated_cart

    async def remove_item(self, user_id: UUID, item_id: int) -> Cart:
        cart = await self.get_or_create_cart(user_id)
        item = await self.cart_repo.get_item_by_id(item_id)
        if item is None or item.cart_id != cart.id:
            raise ValueError("Cart item not found")

        await self.cart_repo.delete_item(item_id)

        updated_cart = await self.cart_repo.get_by_id(cart.id)
        if updated_cart is None:
            raise ValueError("Cart not found")
        return updated_cart

    async def clear_cart(self, user_id: UUID) -> Cart:
        cart = await self.get_or_create_cart(user_id)
        await self.cart_repo.clear_cart(cart.id)

        updated_cart = await self.cart_repo.get_by_id(cart.id)
        if updated_cart is None:
            raise ValueError("Cart not found")
        return updated_cart

    @staticmethod
    def calculate_cart_total(cart: Cart) -> Decimal:
        total = Decimal("0.00")
        for item in cart.items:
            total += Decimal(item.price) * item.quantity
        return total.quantize(Decimal("0.01"))

    @staticmethod
    def count_cart_items(cart: Cart) -> int:
        return sum(item.quantity for item in cart.items)

    @staticmethod
    def find_item(cart: Cart, item_id: int) -> CartItem | None:
        for item in cart.items:
            if item.id == item_id:
                return item
        return None
