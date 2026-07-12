import httpx
import pytest
from fastapi import HTTPException

from app import routes
from dishify_contracts import RecommendRequest


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.is_success = 200 <= status_code < 300

    def json(self) -> dict:
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class _FakeClient:
    def __init__(self, response: _FakeResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def post(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return self.response


def test_proxy_post_preserves_non_json_upstream_errors(monkeypatch):
    monkeypatch.setattr(
        routes.httpx,
        "Client",
        lambda **_kwargs: _FakeClient(_FakeResponse(500, text="upstream exploded")),
    )

    with pytest.raises(HTTPException) as exc:
        routes._proxy_post("http://service/internal/voice", "Ingest service", {})

    assert exc.value.status_code == 500
    assert exc.value.detail == "upstream exploded"


def test_proxy_post_maps_connection_refused_to_503(monkeypatch):
    request = httpx.Request("POST", "http://service/internal/voice")
    error = httpx.ConnectError("[Errno 111] Connection refused", request=request)
    monkeypatch.setattr(routes.httpx, "Client", lambda **_kwargs: _FakeClient(error=error))

    with pytest.raises(HTTPException) as exc:
        routes._proxy_post("http://service/internal/voice", "Ingest service", {})

    assert exc.value.status_code == 503
    assert "Ingest service unavailable" in exc.value.detail
    assert "Connection refused" in exc.value.detail


def test_recommend_preserves_non_json_upstream_errors(monkeypatch):
    monkeypatch.setattr(
        routes.httpx,
        "Client",
        lambda **_kwargs: _FakeClient(_FakeResponse(500, text="retrieval failed")),
    )

    with pytest.raises(HTTPException) as exc:
        routes.recommend.__wrapped__(
            request=None,
            body=RecommendRequest(query="quick eggs", top_k=3),
            token=None,
        )

    assert exc.value.status_code == 500
    assert exc.value.detail == "retrieval failed"
