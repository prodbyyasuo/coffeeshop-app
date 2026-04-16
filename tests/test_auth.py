import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.user import UserRole
from app.schemas.token import Token


@dataclass
class MockUser:
    id: str
    email: str
    username: str
    first_name: str | None
    last_name: str | None
    phone: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthEndpointsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_register_success(self) -> None:
        payload = {
            "email": "new_user@example.com",
            "username": "new_user",
            "password": "strong_password",
            "first_name": "New",
            "last_name": "User",
            "phone": "+1234567890",
        }

        mock_user = MockUser(
            id=str(uuid4()),
            email=payload["email"],
            username=payload["username"],
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            phone=payload["phone"],
            role=UserRole.CUSTOMER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch(
            "app.api.v1.endpoints.auth.AuthService.register",
            new=AsyncMock(return_value=mock_user),
        ):
            response = self.client.post("/api/v1/auth/register", json=payload)

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["email"], payload["email"])
        self.assertEqual(body["username"], payload["username"])
        self.assertEqual(body["role"], UserRole.CUSTOMER.value)
        self.assertNotIn("password", body)
        self.assertNotIn("hashed_password", body)

    def test_register_duplicate_email_returns_400(self) -> None:
        payload = {
            "email": "existing@example.com",
            "username": "existing_user",
            "password": "strong_password",
        }

        with patch(
            "app.api.v1.endpoints.auth.AuthService.register",
            new=AsyncMock(side_effect=ValueError("Email already registered")),
        ):
            response = self.client.post("/api/v1/auth/register", json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Email already registered")

    def test_login_success(self) -> None:
        payload = {
            "email": "existing@example.com",
            "password": "strong_password",
        }

        with patch(
            "app.api.v1.endpoints.auth.AuthService.login",
            new=AsyncMock(
                return_value=Token(access_token="jwt-token-value", token_type="bearer")
            ),
        ):
            response = self.client.post("/api/v1/auth/login", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["access_token"], "jwt-token-value")
        self.assertEqual(body["token_type"], "bearer")

    def test_login_invalid_credentials_returns_401(self) -> None:
        payload = {
            "email": "wrong@example.com",
            "password": "wrong_password",
        }

        with patch(
            "app.api.v1.endpoints.auth.AuthService.login",
            new=AsyncMock(side_effect=ValueError("Invalid email or password")),
        ):
            response = self.client.post("/api/v1/auth/login", json=payload)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid email or password")
        self.assertEqual(response.headers.get("www-authenticate"), "Bearer")


if __name__ == "__main__":
    unittest.main()
