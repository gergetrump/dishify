from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Generate Service", version="0.1.0")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    max_tokens: int = Field(default=256, ge=1, le=4096)


class GenerateResponse(BaseModel):
    output: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "generate-service"}


@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest) -> GenerateResponse:
    # Placeholder response to validate request/response shape.
    return GenerateResponse(output=f"Echo: {payload.prompt}")
