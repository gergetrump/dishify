from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

GENERATE_URL = os.getenv("GENERATE_SERVICE_URL", "http://generate-service:8001")
LLM_URL = os.getenv("LLM_SERVICE_URL", "http://llm-service:8002")
USER_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8003")

app = FastAPI(title="API Gateway", version="0.1.0")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    max_tokens: int = Field(default=256, ge=1, le=4096)


class GenerateResponse(BaseModel):
    output: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    reply: str


class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "api-gateway"}


@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest) -> GenerateResponse:
    return _post_json(GENERATE_URL, "/generate", payload.model_dump(), GenerateResponse)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    return _post_json(LLM_URL, "/chat", payload.model_dump(), ChatResponse)


@app.get("/users", response_model=list[UserResponse])
def list_users() -> list[UserResponse]:
    return _get_json(USER_URL, "/users", list[UserResponse])


@app.post("/users", response_model=UserResponse)
def create_user(payload: CreateUserRequest) -> UserResponse:
    return _post_json(USER_URL, "/users", payload.model_dump(), UserResponse)


def _post_json(base_url: str, path: str, payload: dict, model):
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(f"{base_url}{path}", json=payload)
            response.raise_for_status()
            return model.model_validate(response.json())
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream unavailable: {exc}") from exc


def _get_json(base_url: str, path: str, model):
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{base_url}{path}")
            response.raise_for_status()
            return model.model_validate(response.json())
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream unavailable: {exc}") from exc
