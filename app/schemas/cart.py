from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class CartItemBase(BaseModel):
    product_size_id: int
    quantity: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0, decimal_places=2)


class CartItemCreate(BaseModel):
    product_size_id: int
    quantity: int = Field(default=1, gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., gt=0)


class CartItemResponse(CartItemBase):
    id: int
    cart_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartBase(BaseModel):
    user_id: UUID


class CartResponse(CartBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    items: list[CartItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
