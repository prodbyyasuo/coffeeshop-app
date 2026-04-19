import json
import re
import secrets
import unicodedata
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import verify_token
from app.core.templates import templates
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.cart import CartItemCreate
from app.schemas.order import OrderCreate
from app.schemas.product import (
    ProductCreate,
    ProductSizeCreate,
    ProductSizeUpdate,
    ProductUpdate,
)
from app.schemas.user import UserCreate, UserLogin
from app.services.auth_service import AuthService
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


def _new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _is_checked(value: str | None) -> bool:
    return value in {"on", "true", "1", "yes"}


_CYRILLIC_TO_LATIN = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    transliterated = "".join(_CYRILLIC_TO_LATIN.get(ch, ch) for ch in lowered)
    normalized = unicodedata.normalize("NFKD", transliterated)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug or "item"


async def _build_unique_category_slug(
    db: AsyncSession,
    name: str,
    current_slug: str | None = None,
) -> str:
    repo = CategoryRepository(db)
    base = _slugify(name)
    candidate = base
    index = 2

    while True:
        existing = await repo.get_by_slug(candidate)
        if existing is None or (
            current_slug is not None and existing.slug == current_slug
        ):
            return candidate
        candidate = f"{base}-{index}"
        index += 1


async def _build_unique_product_slug(
    db: AsyncSession,
    name: str,
    current_slug: str | None = None,
) -> str:
    repo = ProductRepository(db)
    base = _slugify(name)
    candidate = base
    index = 2

    while True:
        existing = await repo.get_by_slug(candidate)
        if existing is None or (
            current_slug is not None and existing.slug == current_slug
        ):
            return candidate
        candidate = f"{base}-{index}"
        index += 1


def _secure_cookie() -> bool:
    return not settings.DEBUG


def _set_csrf_cookie(response: HTMLResponse | RedirectResponse, token: str) -> None:
    response.set_cookie(
        key="web_csrf_token",
        value=token,
        httponly=False,
        secure=_secure_cookie(),
        samesite="lax",
        max_age=60 * 60 * 24,
    )


def _set_auth_cookie(response: HTMLResponse | RedirectResponse, token: str) -> None:
    response.set_cookie(
        key="web_access_token",
        value=token,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )


def _clear_auth_cookies(response: RedirectResponse) -> None:
    response.delete_cookie(key="web_access_token", samesite="lax")
    response.delete_cookie(key="web_csrf_token", samesite="lax")


def _csrf_cookie(request: Request) -> str | None:
    return request.cookies.get("web_csrf_token")


def _web_token(request: Request) -> str | None:
    return request.cookies.get("web_access_token")


def _valid_csrf(request: Request, csrf_token: str | None) -> bool:
    cookie_token = _csrf_cookie(request)
    return bool(
        cookie_token and csrf_token and secrets.compare_digest(cookie_token, csrf_token)
    )


def _build_login_context(request: Request, error: str | None = None) -> dict[str, Any]:
    csrf_token = _csrf_cookie(request) or _new_csrf_token()
    return {"request": request, "csrf_token": csrf_token, "error": error}


async def _get_current_web_user(request: Request, db: AsyncSession) -> User | None:
    token = _web_token(request)
    if not token:
        return None

    payload = verify_token(token)
    if payload is None:
        return None

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        return None

    try:
        user_id = UUID(user_id_raw)
    except ValueError:
        return None

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        return None

    return user


def _redirect_login() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


async def _require_admin(request: Request, db: AsyncSession) -> User | None:
    user = await _get_current_web_user(request, db)
    if user is None:
        return None
    if user.role != UserRole.ADMIN:
        raise PermissionError("Admin role required")
    return user


async def _build_home_context(
    request: Request,
    db: AsyncSession,
) -> dict[str, Any]:
    user = await _get_current_web_user(request, db)
    csrf_token = _csrf_cookie(request) or _new_csrf_token()

    product_service = ProductService(db)
    category_service = CategoryService(db)

    products = await product_service.list_products(is_available=True, page=1, size=200)
    categories = await category_service.list_categories(
        only_active=True, skip=0, limit=200
    )

    cart_payload = {"items": [], "items_count": 0, "total_amount": 0.0}
    if user is not None:
        cart_service = CartService(db)
        cart = await cart_service.get_user_cart(user.id)
        cart_payload = _serialize_cart(cart)

    products_payload = [_serialize_product(product) for product in products]
    categories_payload = [
        {
            "id": str(category.id),
            "name": category.name,
            "slug": category.slug,
        }
        for category in categories
    ]
    return {
        "request": request,
        "products": json.dumps(products_payload),
        "categories": json.dumps(categories_payload),
        "cart": cart_payload,
        "error": None,
        "current_user": user,
        "csrf_token": csrf_token,
    }


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    context = await _build_home_context(request, db)
    response = templates.TemplateResponse("layout.html", context)
    _set_csrf_cookie(response, context["csrf_token"])
    return response


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
    if await _get_current_web_user(request, db) is not None:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    context = _build_login_context(request)
    response = templates.TemplateResponse("login.html", context)
    _set_csrf_cookie(response, context["csrf_token"])
    return response


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        context = _build_login_context(request, "Invalid CSRF token.")
        response = templates.TemplateResponse(
            "login.html", context, status_code=status.HTTP_403_FORBIDDEN
        )
        _set_csrf_cookie(response, context["csrf_token"])
        return response

    auth_service = AuthService(db)
    try:
        token = await auth_service.login(UserLogin(email=email, password=password))
    except (ValueError, ValidationError):
        context = _build_login_context(request, "Invalid email or password.")
        response = templates.TemplateResponse(
            "login.html", context, status_code=status.HTTP_401_UNAUTHORIZED
        )
        _set_csrf_cookie(response, context["csrf_token"])
        return response

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    _set_auth_cookie(response, token.access_token)
    _set_csrf_cookie(response, _new_csrf_token())
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: AsyncSession = Depends(get_db)):
    if await _get_current_web_user(request, db) is not None:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    context = _build_login_context(request)
    response = templates.TemplateResponse("register.html", context)
    _set_csrf_cookie(response, context["csrf_token"])
    return response


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(default=""),
    last_name: str = Form(default=""),
    phone: str = Form(default=""),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        context = _build_login_context(request, "Invalid CSRF token.")
        response = templates.TemplateResponse(
            "register.html", context, status_code=status.HTTP_403_FORBIDDEN
        )
        _set_csrf_cookie(response, context["csrf_token"])
        return response

    auth_service = AuthService(db)
    try:
        await auth_service.register(
            UserCreate(
                email=email,
                username=username,
                password=password,
                first_name=first_name or None,
                last_name=last_name or None,
                phone=phone or None,
            )
        )
        token = await auth_service.login(UserLogin(email=email, password=password))
    except (ValueError, ValidationError) as exc:
        context = _build_login_context(request, str(exc))
        response = templates.TemplateResponse(
            "register.html", context, status_code=status.HTTP_400_BAD_REQUEST
        )
        _set_csrf_cookie(response, context["csrf_token"])
        return response

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    _set_auth_cookie(response, token.access_token)
    _set_csrf_cookie(response, _new_csrf_token())
    return response


@router.post("/logout")
async def logout(request: Request, csrf_token: str = Form(...)):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    _clear_auth_cookies(response)
    return response


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_web_user(request, db)
    if user is None:
        return _redirect_login()

    csrf_token = _csrf_cookie(request) or _new_csrf_token()
    response = templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
        },
    )
    _set_csrf_cookie(response, csrf_token)
    return response


@router.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_web_user(request, db)
    if user is None:
        return _redirect_login()

    order_service = OrderService(db)
    orders = await order_service.list_orders(user_id=user.id, skip=0, limit=200)
    return templates.TemplateResponse(
        "orders.html",
        {
            "request": request,
            "orders": orders,
        },
    )


@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail_page(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_current_web_user(request, db)
    if user is None:
        return _redirect_login()

    order_service = OrderService(db)
    try:
        order = await order_service.get_order_by_id(order_id)
    except ValueError:
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": "Order not found",
                "status_code": 404,
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if order.user_id != user.id and user.role != UserRole.ADMIN:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)

    return templates.TemplateResponse(
        "order_detail.html",
        {
            "request": request,
            "order": order,
        },
    )


@router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(
    product_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    product = await service.get_product_by_id(product_id)
    if product is None:
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": "Product not found",
                "status_code": 404,
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )

    payload = _serialize_product(product)
    return templates.TemplateResponse(
        "product_detail.html",
        {
            "request": request,
            "product": payload,
        },
    )


@router.get("/cart", response_class=HTMLResponse)
async def cart_content(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_web_user(request, db)
    if user is None:
        return _redirect_login()

    service = CartService(db)
    cart = await service.get_user_cart(user.id)
    return templates.TemplateResponse(
        "partials/cart_content.html",
        {
            "request": request,
            "cart": _cart_namespace(_serialize_cart(cart)),
        },
    )


@router.get("/cart/count", response_class=HTMLResponse)
async def cart_count(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_web_user(request, db)
    if user is None:
        return HTMLResponse(content="")

    service = CartService(db)
    cart = await service.get_user_cart(user.id)
    payload = _serialize_cart(cart)
    return HTMLResponse(
        content=str(payload["items_count"]) if payload["items_count"] > 0 else ""
    )


@router.post("/cart/add", response_class=HTMLResponse)
async def cart_add(
    request: Request,
    product_size_id: int = Form(...),
    quantity: int = Form(default=1),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_current_web_user(request, db)
    if user is None:
        return _redirect_login()

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

    return response


@router.put("/cart/update/{product_size_id}", response_class=HTMLResponse)
async def cart_update(
    product_size_id: int,
    request: Request,
    quantity: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_current_web_user(request, db)
    if user is None:
        return _redirect_login()

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

    return response


@router.delete("/cart/remove/{product_size_id}", response_class=HTMLResponse)
async def cart_remove(
    product_size_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_current_web_user(request, db)
    if user is None:
        return _redirect_login()

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
        return response

    updated = await service.remove_item(user.id, item.id)
    response = templates.TemplateResponse(
        "partials/cart_content.html",
        {
            "request": request,
            "cart": _cart_namespace(_serialize_cart(updated)),
        },
    )
    return response


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_web_user(request, db)
    if user is None:
        return _redirect_login()

    cart_service = CartService(db)
    cart = await cart_service.get_user_cart(user.id)
    cart_payload = _serialize_cart(cart)
    csrf_token = _csrf_cookie(request) or _new_csrf_token()
    response = templates.TemplateResponse(
        "checkout.html",
        {
            "request": request,
            "cart": _cart_namespace(cart_payload),
            "csrf_token": csrf_token,
        },
    )
    _set_csrf_cookie(response, csrf_token)
    return response


@router.post("/orders", response_class=HTMLResponse)
async def create_order(
    request: Request,
    customer_name: str = Form(...),
    ready_time: str = Form(...),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_current_web_user(request, db)
    if user is None:
        return _redirect_login()
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)

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
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

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
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    category_service = CategoryService(db)
    categories = await category_service.list_categories(skip=0, limit=500)
    csrf_token = _csrf_cookie(request) or _new_csrf_token()
    response = templates.TemplateResponse(
        "admin/categories.html",
        {
            "request": request,
            "categories": categories,
            "csrf_token": csrf_token,
        },
    )
    _set_csrf_cookie(response, csrf_token)
    return response


@router.post("/admin/categories/create")
async def admin_category_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(default=""),
    image_url: str = Form(default=""),
    is_active: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)

    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    service = CategoryService(db)
    try:
        slug = await _build_unique_category_slug(db, name)
        await service.create_category(
            CategoryCreate(
                name=name,
                slug=slug,
                description=description or None,
                image_url=image_url or None,
                is_active=_is_checked(is_active),
            )
        )
    except (ValueError, ValidationError):
        pass

    return RedirectResponse(
        url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/admin/categories/{category_id}/update")
async def admin_category_update(
    category_id: UUID,
    request: Request,
    name: str = Form(...),
    description: str = Form(default=""),
    image_url: str = Form(default=""),
    is_active: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)

    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    service = CategoryService(db)
    try:
        existing = await service.get_category_by_id(category_id)
        if existing is None:
            raise ValueError("Category not found")

        slug = await _build_unique_category_slug(db, name, current_slug=existing.slug)
        await service.update_category(
            category_id,
            CategoryUpdate(
                name=name,
                slug=slug,
                description=description or None,
                image_url=image_url or None,
                is_active=_is_checked(is_active),
            ),
        )
    except (ValueError, ValidationError):
        pass

    return RedirectResponse(
        url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/admin/categories/{category_id}/delete")
async def admin_category_delete(
    category_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)

    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    service = CategoryService(db)
    try:
        await service.delete_category(category_id)
    except ValueError:
        pass

    return RedirectResponse(
        url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    product_service = ProductService(db)
    category_service = CategoryService(db)
    products = await product_service.list_products(page=1, size=500)
    categories = await category_service.list_categories(skip=0, limit=500)
    csrf_token = _csrf_cookie(request) or _new_csrf_token()
    response = templates.TemplateResponse(
        "admin/products.html",
        {
            "request": request,
            "products": products,
            "categories": categories,
            "csrf_token": csrf_token,
        },
    )
    _set_csrf_cookie(response, csrf_token)
    return response


@router.post("/admin/products/create")
async def admin_product_create(
    request: Request,
    category_id: UUID = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    image_url: str = Form(default=""),
    is_available: str | None = Form(default=None),
    size_small_price: Decimal | None = Form(default=None),
    size_medium_price: Decimal | None = Form(default=None),
    size_large_price: Decimal | None = Form(default=None),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)

    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    sizes: list[ProductSizeCreate] = []
    for size_name, size_price in (
        ("Small", size_small_price),
        ("Medium", size_medium_price),
        ("Large", size_large_price),
    ):
        if size_price is not None:
            sizes.append(
                ProductSizeCreate(
                    size=size_name,
                    price=size_price,
                    is_available=True,
                )
            )

    service = ProductService(db)
    try:
        slug = await _build_unique_product_slug(db, name)
        await service.create_product(
            ProductCreate(
                category_id=category_id,
                name=name,
                slug=slug,
                description=description,
                image_url=image_url or None,
                is_available=_is_checked(is_available),
                sizes=sizes,
            )
        )
    except (ValueError, ValidationError):
        pass

    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/admin/products/{product_id}/update")
async def admin_product_update(
    product_id: UUID,
    request: Request,
    category_id: UUID = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    image_url: str = Form(default=""),
    is_available: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)

    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    service = ProductService(db)
    try:
        existing = await service.get_product_by_id(product_id)
        if existing is None:
            raise ValueError("Product not found")

        slug = await _build_unique_product_slug(db, name, current_slug=existing.slug)
        await service.update_product(
            product_id,
            ProductUpdate(
                category_id=category_id,
                name=name,
                slug=slug,
                description=description,
                image_url=image_url or None,
                is_available=_is_checked(is_available),
            ),
        )
    except (ValueError, ValidationError):
        pass

    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/admin/products/{product_id}/delete")
async def admin_product_delete(
    product_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)

    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    service = ProductService(db)
    try:
        await service.delete_product(product_id)
    except ValueError:
        pass

    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    order_service = OrderService(db)
    orders = await order_service.list_orders(skip=0, limit=500)
    csrf_token = _csrf_cookie(request) or _new_csrf_token()
    response = templates.TemplateResponse(
        "admin/orders.html",
        {
            "request": request,
            "orders": orders,
            "csrf_token": csrf_token,
            "order_statuses": ["pending", "processing", "completed", "cancelled"],
        },
    )
    _set_csrf_cookie(response, csrf_token)
    return response


@router.post("/admin/orders/{order_id}/status")
async def admin_order_update_status(
    order_id: int,
    request: Request,
    status_value: str = Form(...),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    service = OrderService(db)
    try:
        await service.update_status(order_id, status_value)
    except ValueError:
        pass

    return RedirectResponse(url="/admin/orders", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/orders/{order_id}/cancel")
async def admin_order_cancel(
    order_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    service = OrderService(db)
    try:
        await service.cancel_order(order_id)
    except ValueError:
        pass

    return RedirectResponse(url="/admin/orders", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    user_service = UserService(db)
    users = await user_service.list_users(skip=0, limit=500)
    csrf_token = _csrf_cookie(request) or _new_csrf_token()
    response = templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "users": users,
            "csrf_token": csrf_token,
        },
    )
    _set_csrf_cookie(response, csrf_token)
    return response


@router.post("/admin/users/{user_id}/role")
async def admin_user_change_role(
    user_id: UUID,
    request: Request,
    role: str = Form(...),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    if user_id == admin_user.id:
        return RedirectResponse(
            url="/admin/users", status_code=status.HTTP_303_SEE_OTHER
        )

    service = UserService(db)
    try:
        await service.change_user_role(user_id, UserRole(role))
    except ValueError:
        pass

    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/users/{user_id}/status")
async def admin_user_change_status(
    user_id: UUID,
    request: Request,
    is_active: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    if user_id == admin_user.id and not _is_checked(is_active):
        return RedirectResponse(
            url="/admin/users", status_code=status.HTTP_303_SEE_OTHER
        )

    service = UserService(db)
    try:
        await service.update_user(user_id, is_active=_is_checked(is_active))
    except ValueError:
        pass

    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/users/{user_id}/delete")
async def admin_user_delete(
    user_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    if user_id == admin_user.id:
        return RedirectResponse(
            url="/admin/users", status_code=status.HTTP_303_SEE_OTHER
        )

    service = UserService(db)
    try:
        await service.delete_user(user_id)
    except ValueError:
        pass

    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/sizes", response_class=HTMLResponse)
async def admin_sizes(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    product_service = ProductService(db)
    products = await product_service.list_products(page=1, size=500)
    csrf_token = _csrf_cookie(request) or _new_csrf_token()
    response = templates.TemplateResponse(
        "admin/sizes.html",
        {
            "request": request,
            "products": products,
            "csrf_token": csrf_token,
        },
    )
    _set_csrf_cookie(response, csrf_token)
    return response


@router.post("/admin/sizes/create")
async def admin_size_create(
    request: Request,
    product_id: UUID = Form(...),
    size: str = Form(...),
    price: Decimal = Form(...),
    is_available: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    service = ProductService(db)
    try:
        await service.create_product_size(
            product_id,
            ProductSizeCreate(
                size=size,
                price=price,
                is_available=_is_checked(is_available),
            ),
        )
    except (ValueError, ValidationError):
        pass

    return RedirectResponse(url="/admin/sizes", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/sizes/{size_id}/update")
async def admin_size_update(
    size_id: int,
    request: Request,
    size: str = Form(...),
    price: Decimal = Form(...),
    is_available: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    service = ProductService(db)
    try:
        await service.update_product_size(
            size_id,
            ProductSizeUpdate(
                size=size,
                price=price,
                is_available=_is_checked(is_available),
            ),
        )
    except (ValueError, ValidationError):
        pass

    return RedirectResponse(url="/admin/sizes", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/sizes/{size_id}/delete")
async def admin_size_delete(
    size_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not _valid_csrf(request, csrf_token):
        return HTMLResponse("Invalid CSRF token", status_code=status.HTTP_403_FORBIDDEN)
    try:
        admin_user = await _require_admin(request, db)
    except PermissionError:
        return HTMLResponse("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if admin_user is None:
        return _redirect_login()

    service = ProductService(db)
    try:
        await service.delete_product_size(size_id)
    except ValueError:
        pass

    return RedirectResponse(url="/admin/sizes", status_code=status.HTTP_303_SEE_OTHER)
