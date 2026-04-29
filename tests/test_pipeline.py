"""End-to-end pipeline tests via FastAPI's TestClient.

Hits the real /recommend endpoint with a seeded SQLite. Gemini-dependent
stages are expected to be 'skipped' since the GEMINI_API_KEY env var is
scrubbed by conftest.
"""

from __future__ import annotations

import pytest
from app.db import SessionLocal


@pytest.fixture()
def client(seed_recipes):
	# Import lazily so the env scrubbing in conftest is in place first.
	from app.main import app
	from fastapi.testclient import TestClient

	with TestClient(app) as c:
		yield c


def _stages_by_name(payload: dict) -> dict[str, dict]:
	return {s["name"]: s for s in payload["stages"]}


def test_health_returns_recipe_count(client) -> None:
	body = client.get("/health").json()
	assert body["status"] == "ok"
	assert body["recipe_count"] == 4


def test_recommend_validates_empty_ingredients(client) -> None:
	assert client.post("/recommend", json={"ingredients": []}).status_code == 422


def test_recommend_response_includes_titles_and_links(client) -> None:
	payload = client.post(
		"/recommend",
		json={"ingredients": ["tomato", "pasta"], "profile": {"diet": "omnivore"}, "top_k": 3},
	).json()
	assert payload["normalized_ingredients"] == ["tomato", "pasta"]
	assert payload["recommendations"], "expected at least one recommendation"
	first = payload["recommendations"][0]
	# Bug 1 -- titles + ingredients should be in the response.
	assert first["title"]
	assert isinstance(first["ingredients"], list) and first["ingredients"]
	assert isinstance(first["score"], float)


def test_recommend_pool_size_respects_diet(client) -> None:
	payload = client.post(
		"/recommend",
		json={"ingredients": ["tomato"], "profile": {"diet": "vegan"}},
	).json()
	# Only the vegan recipe (id 1) survives.
	assert payload["candidate_pool_size"] == 1


def test_recommend_skips_llm_stages_without_key(client) -> None:
	payload = client.post(
		"/recommend",
		json={"ingredients": ["tomato", "pasta"], "profile": {"diet": "vegan"}},
	).json()
	stages = _stages_by_name(payload)
	assert stages["normalize"]["status"] == "ok"
	assert stages["hard_filter"]["status"] == "ok"
	assert stages["vector_retrieval"]["status"] == "skipped"
	assert stages["rule_based_scoring"]["status"] == "ok"
	assert stages["llm_reasoning"]["status"] == "skipped"


def test_recommend_records_per_stage_latency(client) -> None:
	payload = client.post(
		"/recommend",
		json={"ingredients": ["tomato"], "profile": {"diet": "omnivore"}},
	).json()
	for stage in payload["stages"]:
		# Bug 9 -- latency_ms should be populated for every stage that ran.
		assert stage["latency_ms"] is not None
		assert stage["latency_ms"] >= 0


def test_request_id_header_is_added(client) -> None:
	resp = client.get("/health")
	assert "x-request-id" in {k.lower() for k in resp.headers}


def test_token_match_chicken_finds_chicken_breasts(client) -> None:
	# Bug 2 regression: the user typing 'chicken' must match the recipe's
	# 'chicken breasts' ingredient.
	payload = client.post(
		"/recommend",
		json={"ingredients": ["chicken"], "profile": {"diet": "omnivore"}, "top_k": 5},
	).json()
	titles = [r["title"] for r in payload["recommendations"]]
	assert "Chicken Curry" in titles
	chicken_curry = next(r for r in payload["recommendations"] if r["title"] == "Chicken Curry")
	assert "chicken breasts" in chicken_curry["available_ingredients"]


def test_egg_does_not_match_eggplant(client) -> None:
	# Bug 2 regression: word-level matching must keep 'egg' from matching 'eggplant'.
	payload = client.post(
		"/recommend",
		json={"ingredients": ["egg"], "profile": {"diet": "omnivore"}, "top_k": 5},
	).json()
	eggplant_card = next(
		(r for r in payload["recommendations"] if r["title"] == "Eggplant Parmesan"),
		None,
	)
	if eggplant_card is not None:
		assert "eggplant" not in eggplant_card["available_ingredients"]


def test_session_fixture_persists_via_pipeline(seed_recipes) -> None:
	# Sanity check: the same seeded data is visible through SessionLocal.
	from app.db import count

	with SessionLocal() as s:
		assert count(s) == 4
