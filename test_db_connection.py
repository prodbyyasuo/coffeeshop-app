import asyncio
import asyncpg
from app.config import settings


async def test_connection():
    try:
        # Парсим DATABASE_URL
        url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "")
        print(f"Trying to connect with URL: {settings.DATABASE_URL}")

        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="coffee_user",
            password="coffee_pass_2026",
            database="coffee_shop",
        )

        version = await conn.fetchval("SELECT version()")
        print(f"Connected successfully!")
        print(f"PostgreSQL version: {version}")

        await conn.close()
        print("Connection closed")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_connection())
