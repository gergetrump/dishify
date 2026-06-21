#!/usr/bin/env python3
"""Smoke test for the microservice API contract at http://localhost:8000."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"


def _request(
    method: str, path: str, body: dict | None = None
) -> tuple[int, dict | str]:
    url = f"{BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(payload)
        except json.JSONDecodeError:
            return exc.code, payload


def main() -> int:
    print("GET /health")
    try:
        status, health = _request("GET", "/health")
    except urllib.error.URLError as exc:
        print(
            f"SKIP: gateway not reachable at {BASE_URL}: {exc.reason}", file=sys.stderr
        )
        return 0
    if status != 200:
        print(f"FAIL: health returned {status}: {health}", file=sys.stderr)
        return 1
    if health.get("status") != "ok" or health.get("service") != "dishify-backend":
        print(f"FAIL: unexpected health payload: {health}", file=sys.stderr)
        return 1
    print("OK")

    print("POST /recommend")
    recommend_body = {
        "query": "creamy tomato pasta with spinach",
        "top_k": 3,
        "available_ingredients": [
            {"name": "penne", "quantity": 12, "unit": "oz", "raw_text": "12 oz penne"},
            {"name": "tomato", "quantity": None, "unit": None, "raw_text": "tomato"},
        ],
        "exclusion_restrictions": ["shellfish_allergy", "nut_allergy", "vegetarian"],
    }
    status, payload = _request("POST", "/recommend", recommend_body)
    if status == 503:
        print(
            f"SKIP: recommend unavailable (index Qdrant first): {payload}",
            file=sys.stderr,
        )
        return 0
    if status != 200:
        print(f"FAIL: recommend returned {status}: {payload}", file=sys.stderr)
        return 1

    results = payload.get("results") or []
    stages = payload.get("stages") or []
    if not results:
        print("FAIL: recommend returned no results", file=sys.stderr)
        return 1
    if len(stages) != 3:
        print(f"FAIL: expected 3 pipeline stages, got {len(stages)}", file=sys.stderr)
        return 1

    required_result_keys = {"rank", "id", "title", "score", "reasoning"}
    first = results[0]
    if not required_result_keys.issubset(first.keys()):
        print(f"FAIL: result missing keys: {first}", file=sys.stderr)
        return 1

    print(f"OK ({len(results)} results, stages={[s.get('name') for s in stages]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
