from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal


class OrderItemBase(BaseModel):
    product_size_id: int
    quantity: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0, decimal_places=2)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255)
    ready_time: str = Field(..., min_length=1, max_length=10)
    total_amount: Decimal = Field(..., gt=0, decimal_places=2)
    status: str = Field(default="pending", max_length=50)


class OrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255)
    ready_time: str = Field(..., min_length=1, max_length=10)


class OrderUpdate(BaseModel):
    status: str = Field(..., max_length=50)


class OrderResponse(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
