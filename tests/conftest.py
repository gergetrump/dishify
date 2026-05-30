"""Shared pytest fixtures.

The ``backend/`` directory is added to ``sys.path`` via ``pythonpath`` in
``pyproject.toml`` so tests can ``from app... import ...`` directly.

We pin DATABASE_URL / EMBEDDINGS_PATH / etc. to a temp dir at module load
time -- *before* any ``app.*`` import -- so the engine is created against
the test SQLite file. Tests then truncate the recipes table between runs to
stay hermetic without paying for module reloads.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

# ---- Pre-import environment shim -------------------------------------------
# This block must run BEFORE the first ``from app... import ...`` so the
# SQLAlchemy engine is bound to the test SQLite file.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="dishify-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR / 'test.db'}"
os.environ["EMBEDDINGS_PATH"] = str(_TEST_DIR / "embeddings.npz")
os.environ["EMBEDDING_CACHE_PATH"] = str(_TEST_DIR / "embeddings_cache.npz")
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("QDRANT_URL", None)
# ---------------------------------------------------------------------------

import pytest
from app.db import Recipe, SessionLocal, create_all


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Iterator[None]:
    create_all()
    yield


@pytest.fixture(autouse=True)
def _truncate_recipes() -> Iterator[None]:
    """Wipe recipes between tests so each test starts from a clean slate."""

    with SessionLocal() as s:
        s.query(Recipe).delete()
        s.commit()
    yield


@pytest.fixture()
def session() -> Iterator[object]:
    with SessionLocal() as s:
        yield s


@pytest.fixture()
def seed_recipes(session) -> list[Recipe]:
    """Insert a small but representative corpus."""

    recipes = [
        Recipe(
            id=1,
            title="Tomato Pasta",
            ingredients_clean=["tomato", "pasta", "basil", "olive oil"],
            ingredients_raw=[
                "1 cup tomato sauce",
                "200g pasta",
                "fresh basil",
                "olive oil",
            ],
            directions=["Boil pasta.", "Mix with sauce."],
            diet="vegan",
            allergens=["gluten"],
            source="test",
        ),
        Recipe(
            id=2,
            title="Chicken Curry",
            ingredients_clean=["chicken breasts", "onion", "curry powder", "yogurt"],
            ingredients_raw=["2 chicken breasts", "1 onion", "2 tbsp curry", "yogurt"],
            directions=["Cook chicken.", "Stir in curry."],
            diet="omnivore",
            allergens=["dairy"],
            source="test",
        ),
        Recipe(
            id=3,
            title="Peanut Butter Cookies",
            ingredients_clean=["peanut butter", "sugar", "egg"],
            ingredients_raw=["1 cup peanut butter", "1 cup sugar", "1 egg"],
            directions=["Bake."],
            diet="vegetarian",
            allergens=["peanuts", "eggs"],
            source="test",
        ),
        Recipe(
            id=4,
            title="Eggplant Parmesan",
            ingredients_clean=["eggplant", "mozzarella", "tomato sauce"],
            ingredients_raw=["1 large eggplant", "mozzarella", "tomato sauce"],
            directions=["Bake."],
            diet="vegetarian",
            allergens=["dairy"],
            source="test",
        ),
    ]
    session.add_all(recipes)
    session.commit()
    return recipes
