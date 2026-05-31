from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="LLM Service", version="0.1.0")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "llm-service"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    # Placeholder response to validate request/response shape.
    return ChatResponse(reply=f"LLM stub: {payload.message}")
