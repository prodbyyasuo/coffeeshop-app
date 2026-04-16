import json
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.templates import templates
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.cart import CartItemCreate
from app.schemas.order import OrderCreate
from app.services.cart_service import CartService
from app.services.category_service import CategoryService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.user_service import UserService

router = APIRouter()


def _decimal_to_float(value: Decimal | float | int) -> float:
    return float(value)


def _serialize_product(product: Any) -> dict[str, Any]:
    return {
        "id": str(product.id),
        "name": product.name,
        "description": product.description,
        "image_path": product.image_url,
        "category": {
            "id": str(product.category.id),
            "name": product.category.name,
            "slug": product.category.slug,
        }
        if product.category
        else None,
        "product_sizes": [
            {
                "id": size.id,
                "price": _decimal_to_float(size.price),
                "size": {
                    "name": size.size,
                    "volume": "",
                    "unit": "",
                },
                "is_available": size.is_available,
            }
            for size in product.sizes
            if size.is_available
        ],
    }


def _serialize_cart(cart: Any) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    items_count = 0
    total_amount = 0.0

    for item in cart.items:
        product = item.product_size.product if item.product_size else None
        price = _decimal_to_float(item.price)
        total_price = price * item.quantity
        items_count += item.quantity
        total_amount += total_price
        items.append(
            {
                "id": item.id,
                "product_size_id": item.product_size_id,
                "product_name": product.name if product else "Unknown",
                "size_name": item.product_size.size if item.product_size else "",
                "image_path": product.image_url if product else None,
                "quantity": item.quantity,
                "price": price,
                "total_price": total_price,
            }
        )

    return {
        "items": items,
        "items_count": items_count,
        "total_amount": round(total_amount, 2),
    }


def _cart_namespace(cart_data: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        items=cart_data["items"],
        items_count=cart_data["items_count"],
        total_amount=cart_data["total_amount"],
    )


def _cookie_user_id(request: Request) -> UUID | None:
    raw = request.cookies.get("web_user_id")
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


async def _get_or_create_web_user(
    request: Request,
    db: AsyncSession,
) -> tuple[User, bool]:
    user_repo = UserRepository(db)
    cookie_id = _cookie_user_id(request)

    if cookie_id is not None:
        existing = await user_repo.get_by_id(cookie_id)
        if existing is not None and existing.is_active:
            return existing, False

    token = uuid4().hex[:10]
    user = await user_repo.create(
        email=f"guest_{token}@local.coffee",
        username=f"guest_{token}",
        hashed_password=get_password_hash(uuid4().hex),
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    return user, True


def _attach_user_cookie(response: HTMLResponse, user_id: UUID) -> None:
    response.set_cookie(
        key="web_user_id",
        value=str(user_id),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )


async def _build_home_context(
    request: Request,
    db: AsyncSession,
) -> tuple[dict[str, Any], UUID]:
    user, _ = await _get_or_create_web_user(request, db)

    product_service = ProductService(db)
    category_service = CategoryService(db)
    cart_service = CartService(db)

    products = await product_service.list_products(is_available=True, page=1, size=200)
    categories = await category_service.list_categories(
        only_active=True, skip=0, limit=200
    )
    cart = await cart_service.get_user_cart(user.id)

    products_payload = [_serialize_product(product) for product in products]
    categories_payload = [
        {
            "id": str(category.id),
            "name": category.name,
            "slug": category.slug,
        }
        for category in categories
    ]
    cart_payload = _serialize_cart(cart)

    return (
        {
            "request": request,
            "products": json.dumps(products_payload),
            "categories": json.dumps(categories_payload),
            "cart": cart_payload,
            "error": None,
        },
        user.id,
    )


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    context, user_id = await _build_home_context(request, db)
    response = templates.TemplateResponse("layout.html", context)
    _attach_user_cookie(response, user_id)
    return response


@router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(
    product_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user, _ = await _get_or_create_web_user(request, db)
    service = ProductService(db)
    product = await service.get_product_by_id(product_id)
    if product is None:
        response = templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": "Product not found",
                "status_code": 404,
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )
        _attach_user_cookie(response, user.id)
        return response

    payload = _serialize_product(product)
    response = templates.TemplateResponse(
        "product_detail.html",
        {
            "request": request,
            "product": payload,
        },
    )
    _attach_user_cookie(response, user.id)
    return response


@router.get("/cart", response_class=HTMLResponse)
async def cart_content(request: Request, db: AsyncSession = Depends(get_db)):
    user, _ = await _get_or_create_web_user(request, db)
    service = CartService(db)
    cart = await service.get_user_cart(user.id)
    response = templates.TemplateResponse(
        "partials/cart_content.html",
        {
            "request": request,
            "cart": _cart_namespace(_serialize_cart(cart)),
        },
    )
    _attach_user_cookie(response, user.id)
    return response


@router.get("/cart/count", response_class=HTMLResponse)
async def cart_count(request: Request, db: AsyncSession = Depends(get_db)):
    user, _ = await _get_or_create_web_user(request, db)
    service = CartService(db)
    cart = await service.get_user_cart(user.id)
    payload = _serialize_cart(cart)
    response = HTMLResponse(
        content=str(payload["items_count"]) if payload["items_count"] > 0 else ""
    )
    _attach_user_cookie(response, user.id)
    return response


@router.post("/cart/add", response_class=HTMLResponse)
async def cart_add(
    request: Request,
    product_size_id: int = Form(...),
    quantity: int = Form(default=1),
    db: AsyncSession = Depends(get_db),
):
    user, _ = await _get_or_create_web_user(request, db)
    service = CartService(db)
    try:
        cart = await service.add_item(
            user.id,
            CartItemCreate(product_size_id=product_size_id, quantity=quantity),
        )
        response = templates.TemplateResponse(
            "partials/cart_content.html",
            {
                "request": request,
                "cart": _cart_namespace(_serialize_cart(cart)),
            },
        )
    except ValueError as exc:
        response = templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": str(exc),
                "status_code": 400,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    _attach_user_cookie(response, user.id)
    return response


@router.put("/cart/update/{product_size_id}", response_class=HTMLResponse)
async def cart_update(
    product_size_id: int,
    request: Request,
    quantity: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user, _ = await _get_or_create_web_user(request, db)
    service = CartService(db)
    cart = await service.get_user_cart(user.id)
    item = next(
        (it for it in cart.items if it.product_size_id == product_size_id), None
    )

    if item is None:
        response = templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": "Cart item not found",
                "status_code": 404,
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )
        _attach_user_cookie(response, user.id)
        return response

    try:
        updated = await service.update_item_quantity(user.id, item.id, quantity)
        response = templates.TemplateResponse(
            "partials/cart_content.html",
            {
                "request": request,
                "cart": _cart_namespace(_serialize_cart(updated)),
            },
        )
    except ValueError as exc:
        response = templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": str(exc),
                "status_code": 400,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    _attach_user_cookie(response, user.id)
    return response


@router.delete("/cart/remove/{product_size_id}", response_class=HTMLResponse)
async def cart_remove(
    product_size_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user, _ = await _get_or_create_web_user(request, db)
    service = CartService(db)
    cart = await service.get_user_cart(user.id)
    item = next(
        (it for it in cart.items if it.product_size_id == product_size_id), None
    )

    if item is None:
        response = templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": "Cart item not found",
                "status_code": 404,
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )
        _attach_user_cookie(response, user.id)
        return response

    updated = await service.remove_item(user.id, item.id)
    response = templates.TemplateResponse(
        "partials/cart_content.html",
        {
            "request": request,
            "cart": _cart_namespace(_serialize_cart(updated)),
        },
    )
    _attach_user_cookie(response, user.id)
    return response


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: AsyncSession = Depends(get_db)):
    user, _ = await _get_or_create_web_user(request, db)
    cart_service = CartService(db)
    cart = await cart_service.get_user_cart(user.id)
    cart_payload = _serialize_cart(cart)
    response = templates.TemplateResponse(
        "checkout.html",
        {
            "request": request,
            "cart": _cart_namespace(cart_payload),
        },
    )
    _attach_user_cookie(response, user.id)
    return response


@router.post("/orders", response_class=HTMLResponse)
async def create_order(
    request: Request,
    customer_name: str = Form(...),
    ready_time: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user, _ = await _get_or_create_web_user(request, db)
    order_service = OrderService(db)
    try:
        order = await order_service.create_from_cart(
            user.id,
            OrderCreate(customer_name=customer_name, ready_time=ready_time),
        )
        response = templates.TemplateResponse(
            "order_success.html",
            {
                "request": request,
                "order": order,
                "message": "Your order has been successfully placed.",
            },
        )
    except ValueError as exc:
        response = templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": str(exc),
                "status_code": 400,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    _attach_user_cookie(response, user.id)
    return response


@router.get("/catalog/category/{slug}", response_class=HTMLResponse)
async def catalog_by_category(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    category_service = CategoryService(db)
    product_service = ProductService(db)

    categories = await category_service.list_categories(
        only_active=True, skip=0, limit=200
    )
    category = next((cat for cat in categories if cat.slug == slug), None)
    if category is None:
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": "Category not found",
                "status_code": 404,
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )

    products = await product_service.list_products(
        category_id=category.id,
        is_available=True,
        page=1,
        size=200,
    )
    products = [product for product in products if product.is_available]
    return templates.TemplateResponse(
        "partials/product_list.html",
        {
            "request": request,
            "products": [_serialize_product(product) for product in products],
            "search_query": None,
        },
    )


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    product_service = ProductService(db)
    category_service = CategoryService(db)
    order_service = OrderService(db)

    products = await product_service.list_products(page=1, size=500)
    categories = await category_service.list_categories(skip=0, limit=500)
    orders = await order_service.list_orders(skip=0, limit=200)

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "orders": orders,
            "active_products": len([item for item in products if item.is_available]),
            "total_products": len(products),
            "active_categories": len([item for item in categories if item.is_active]),
            "total_categories": len(categories),
        },
    )


@router.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(request: Request, db: AsyncSession = Depends(get_db)):
    category_service = CategoryService(db)
    categories = await category_service.list_categories(skip=0, limit=500)
    return templates.TemplateResponse(
        "admin/categories.html",
        {
            "request": request,
            "categories": categories,
        },
    )


@router.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request, db: AsyncSession = Depends(get_db)):
    product_service = ProductService(db)
    products = await product_service.list_products(page=1, size=500)
    return templates.TemplateResponse(
        "admin/products.html",
        {
            "request": request,
            "products": products,
        },
    )


@router.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders(request: Request, db: AsyncSession = Depends(get_db)):
    order_service = OrderService(db)
    orders = await order_service.list_orders(skip=0, limit=500)
    return templates.TemplateResponse(
        "admin/orders.html",
        {
            "request": request,
            "orders": orders,
        },
    )


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    users = await user_service.list_users(skip=0, limit=500)
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "users": users,
        },
    )


@router.get("/admin/sizes", response_class=HTMLResponse)
async def admin_sizes(request: Request, db: AsyncSession = Depends(get_db)):
    product_service = ProductService(db)
    products = await product_service.list_products(page=1, size=500)
    sizes: list[dict[str, Any]] = []
    for product in products:
        for size in product.sizes:
            sizes.append(
                {
                    "product_name": product.name,
                    "size": size.size,
                    "price": _decimal_to_float(size.price),
                    "is_available": size.is_available,
                }
            )
    return templates.TemplateResponse(
        "admin/sizes.html",
        {
            "request": request,
            "sizes": sizes,
        },
    )
