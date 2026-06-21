import pytest
from pydantic import ValidationError

from dishify_contracts import (
    LoginRequest,
    LogoutRequest,
    RecommendRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdatePreferencesRequest,
    UserPreferences,
)


class TestLoginRequest:
    def test_valid(self):
        req = LoginRequest(username="user", password="pass")
        assert req.username == "user"

    def test_rejects_empty_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="pass")

    def test_rejects_empty_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="user", password="")


class TestRefreshRequest:
    def test_valid(self):
        req = RefreshRequest(refresh_token="rt-123")
        assert req.refresh_token == "rt-123"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            RefreshRequest(refresh_token="")


class TestLogoutRequest:
    def test_valid(self):
        req = LogoutRequest(refresh_token="rt-123")
        assert req.refresh_token == "rt-123"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            LogoutRequest(refresh_token="")


class TestRegisterRequest:
    def test_valid(self):
        req = RegisterRequest(
            username="testuser",
            email="test@example.com",
            password="securepass",
        )
        assert req.username == "testuser"

    def test_rejects_short_username(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="ab", email="a@b.com", password="securepass")

    def test_rejects_short_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser", email="a@b.com", password="short")

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser", email="not-email", password="securepass")


class TestTokenResponse:
    def test_minimal(self):
        t = TokenResponse(access_token="at", expires_in=300)
        assert t.token_type == "Bearer"
        assert t.refresh_token is None

    def test_with_refresh(self):
        t = TokenResponse(
            access_token="at",
            expires_in=300,
            refresh_token="rt",
        )
        assert t.refresh_token == "rt"


class TestUserPreferences:
    def test_defaults_to_empty(self):
        prefs = UserPreferences()
        assert prefs.exclusion_restrictions == []

    def test_with_restrictions(self):
        prefs = UserPreferences(exclusion_restrictions=["vegetarian", "nut_allergy"])
        assert len(prefs.exclusion_restrictions) == 2


class TestRecommendRequest:
    def test_minimal(self):
        req = RecommendRequest(query="pasta dinner")
        assert req.query == "pasta dinner"

    def test_with_all_fields(self):
        req = RecommendRequest(
            query="pasta",
            top_k=5,
            available_ingredients=[],
            exclusion_restrictions=["vegetarian"],
        )
        assert req.top_k == 5
