from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.recommend import router as recommend_router
from app.config import settings

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
	yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(recommend_router)
