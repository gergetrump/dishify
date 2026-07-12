import logging
import threading
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.config import settings
from app.routes import router

load_dotenv()

logger = logging.getLogger(__name__)


def _warm_store() -> None:
    """Load the embedding model and run one tiny encode so the first real
    request doesn't pay the cold-start cost."""
    try:
        from app.store import get_recipe_store

        store = get_recipe_store()
        store.embedding_model.encode(["warmup"])
        logger.info("Retrieval store warmed up")
    except Exception:
        logger.exception("Retrieval warmup failed (will load on first request)")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Warm in the background so startup/health checks aren't blocked by model load.
    threading.Thread(target=_warm_store, daemon=True).start()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
