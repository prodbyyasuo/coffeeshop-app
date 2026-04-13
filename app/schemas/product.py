from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class ProductSizeBase(BaseModel):
    size: str = Field(..., min_length=1, max_length=50)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    is_available: bool = True


class ProductSizeCreate(ProductSizeBase):
    pass


class ProductSizeUpdate(BaseModel):
    size: str | None = None
    price: Decimal | None = Field(None, gt=0, decimal_places=2)
    is_available: bool | None = None


class ProductSizeResponse(ProductSizeBase):
    id: int
    product_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200)
    description: str
    image_url: str | None = None
    is_available: bool = True
    category_id: UUID


class ProductCreate(ProductBase):
    sizes: list[ProductSizeCreate] = []


class ProductUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    image_url: str | None = None
    is_available: bool | None = None
    category_id: UUID | None = None


class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    sizes: list[ProductSizeResponse] = []

    model_config = ConfigDict(from_attributes=True)
