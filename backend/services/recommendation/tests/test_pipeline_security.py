from app import pipeline
from dishify_contracts import ParsedIngredientModel, RecommendRequest, RetrievedRecipe


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300
        self.text = ""

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if not self.is_success:
            raise RuntimeError(f"unexpected status {self.status_code}")


def test_guarded_explanation_uses_deterministic_fallback(monkeypatch):
    recipe = RetrievedRecipe(
        id=101,
        score=0.9,
        title="Quick Tomato Pasta",
        ingredients=["tomato", "pasta"],
        parsed_ingredients=[],
        inventory_matched=["tomato"],
        inventory_missing=["pasta"],
    )
    responses = iter(
        [
            _FakeResponse({"recipes": [recipe.model_dump()], "latency_ms": 1}),
            _FakeResponse(
                {
                    "results": [],
                    "latency_ms": 2,
                    "guardrail_triggered": True,
                }
            ),
        ]
    )

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, *_args, **_kwargs):
            return next(responses)

    monkeypatch.setattr(pipeline.httpx, "Client", FakeClient)
    monkeypatch.setattr(pipeline.settings, "enable_llm_reasoning", True)
    monkeypatch.setattr(
        pipeline,
        "score_recipes_by_inventory",
        lambda recipes, *_args, **_kwargs: recipes,
    )

    result = pipeline.run_recommend_pipeline(
        RecommendRequest(
            query="quick tomato dinner",
            top_k=1,
            available_ingredients=[ParsedIngredientModel(name="tomato")],
        )
    )

    assert result.stages[-1].status == "guarded"
    assert result.results[0].reasoning.positive == [
        "Uses ingredients you have: tomato."
    ]
    assert result.results[0].reasoning.negative == ["You may need: pasta."]
    assert "JAILBREAK_SUCCESS_7KQ9" not in result.model_dump_json()
