from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, get_current_admin_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderResponse, OrderUpdate
from app.services.order_service import OrderService

router = APIRouter()


def _ensure_order_access(order_user_id: UUID, current_user: User) -> None:
    if current_user.role == UserRole.ADMIN:
        return
    if order_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    status_filter: str | None = Query(default=None, alias="status"),
    customer_name: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)

    user_id: UUID | None = None
    if current_user.role != UserRole.ADMIN:
        user_id = current_user.id

    return await service.list_orders(
        skip=skip,
        limit=limit,
        status=status_filter,
        customer_name=customer_name,
        user_id=user_id,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    try:
        order = await service.get_order_by_id(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    _ensure_order_access(order.user_id, current_user)
    return order


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    customer_name = payload.customer_name
    if current_user.role != UserRole.ADMIN:
        customer_name = current_user.username

    normalized_payload = OrderCreate(
        customer_name=customer_name,
        ready_time=payload.ready_time,
    )

    try:
        return await service.create_from_cart(current_user.id, normalized_payload)
    except ValueError as exc:
        message = str(exc)
        code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in message.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=message)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    payload: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    service = OrderService(db)
    try:
        return await service.update_status(order_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    try:
        order = await service.get_order_by_id(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    _ensure_order_access(order.user_id, current_user)

    try:
        await service.cancel_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
