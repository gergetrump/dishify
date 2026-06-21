from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.config import settings
from app.routes import router

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
