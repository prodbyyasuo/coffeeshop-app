import asyncio
import os
import re
import sys
import unicodedata
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.db.session import AsyncSessionLocal
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug or "item"


MENU = {
    "Coffee Classics": [
        {
            "name": "Espresso",
            "description": "Strong and rich espresso shot.",
            "image_url": None,
            "sizes": {"Single": Decimal("2.90"), "Double": Decimal("3.90")},
        },
        {
            "name": "Americano",
            "description": "Espresso with hot water.",
            "image_url": None,
            "sizes": {
                "Small": Decimal("3.20"),
                "Medium": Decimal("3.90"),
                "Large": Decimal("4.50"),
            },
        },
        {
            "name": "Cappuccino",
            "description": "Balanced espresso, milk and foam.",
            "image_url": None,
            "sizes": {
                "Small": Decimal("3.80"),
                "Medium": Decimal("4.60"),
                "Large": Decimal("5.30"),
            },
        },
        {
            "name": "Latte",
            "description": "Smooth milk coffee with gentle taste.",
            "image_url": None,
            "sizes": {
                "Small": Decimal("4.00"),
                "Medium": Decimal("4.90"),
                "Large": Decimal("5.70"),
            },
        },
        {
            "name": "Caramel Latte",
            "description": "Latte with caramel syrup and foam.",
            "image_url": None,
            "sizes": {
                "Small": Decimal("4.50"),
                "Medium": Decimal("5.30"),
                "Large": Decimal("6.10"),
            },
        },
    ],
    "Cold Coffee": [
        {
            "name": "Iced Americano",
            "description": "Refreshing chilled americano with ice.",
            "image_url": None,
            "sizes": {
                "Small": Decimal("3.60"),
                "Medium": Decimal("4.20"),
                "Large": Decimal("4.90"),
            },
        },
        {
            "name": "Iced Latte",
            "description": "Cold milk coffee served over ice.",
            "image_url": None,
            "sizes": {
                "Small": Decimal("4.40"),
                "Medium": Decimal("5.20"),
                "Large": Decimal("5.90"),
            },
        },
    ],
}


def _collect_project_images() -> list[str]:
    static_images = Path(PROJECT_ROOT) / "app" / "static" / "images"
    candidates: list[Path] = []

    products_dir = static_images / "products"
    if products_dir.exists():
        candidates.extend(sorted(products_dir.glob("*.png")))
        candidates.extend(sorted(products_dir.glob("*.jpg")))
        candidates.extend(sorted(products_dir.glob("*.jpeg")))

    candidates.extend(sorted(static_images.glob("*.png")))
    candidates.extend(sorted(static_images.glob("*.jpg")))
    candidates.extend(sorted(static_images.glob("*.jpeg")))

    filtered: list[str] = []
    for path in candidates:
        if path.exists() and path.stat().st_size > 0:
            rel = path.relative_to(Path(PROJECT_ROOT) / "app" / "static")
            filtered.append(f"/static/{rel.as_posix()}")

    return filtered


async def upsert_menu() -> None:
    images = _collect_project_images()
    if not images:
        raise RuntimeError("No non-empty images found in app/static/images")

    image_index = 0

    async with AsyncSessionLocal() as session:
        category_repo = CategoryRepository(session)
        product_repo = ProductRepository(session)

        for category_name, products in MENU.items():
            category_slug = slugify(category_name)
            category = await category_repo.get_by_slug(category_slug)

            if category is None:
                category = await category_repo.create(
                    name=category_name,
                    slug=category_slug,
                    description=f"{category_name} menu section",
                    image_url=None,
                    is_active=True,
                )
            else:
                await category_repo.update(
                    category.id,
                    name=category_name,
                    description=f"{category_name} menu section",
                    is_active=True,
                )

            for item in products:
                product_slug = slugify(item["name"])
                product = await product_repo.get_by_slug(product_slug)

                if product is None:
                    image_url = item["image_url"] or images[image_index % len(images)]
                    image_index += 1
                    product = await product_repo.create(
                        category_id=category.id,
                        name=item["name"],
                        slug=product_slug,
                        description=item["description"],
                        image_url=image_url,
                        is_available=True,
                    )
                else:
                    image_url = item["image_url"] or product.image_url
                    if not image_url:
                        image_url = images[image_index % len(images)]
                        image_index += 1
                    await product_repo.update(
                        product.id,
                        category_id=category.id,
                        name=item["name"],
                        description=item["description"],
                        image_url=image_url,
                        is_available=True,
                    )

                refreshed = await product_repo.get_by_id(product.id)
                if refreshed is None:
                    continue

                existing_by_size = {size.size: size for size in refreshed.sizes}
                target_sizes = item["sizes"]

                for size_name, price in target_sizes.items():
                    existing = existing_by_size.get(size_name)
                    if existing is None:
                        await product_repo.create_size(
                            product_id=refreshed.id,
                            size=size_name,
                            price=price,
                            is_available=True,
                        )
                    else:
                        await product_repo.update_size(
                            existing.id,
                            price=price,
                            is_available=True,
                        )

                for size_name, size in existing_by_size.items():
                    if size_name not in target_sizes:
                        await product_repo.delete_size(size.id)

        print("Menu seed completed.")


if __name__ == "__main__":
    asyncio.run(upsert_menu())
