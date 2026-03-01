"""FastAPI application entry point for the OpenEMR AI agent."""

import uuid

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent.graph import run_agent
from src.config import OPENEMR_BASE_URL
from src.observability.tracing import log_feedback

app = FastAPI(title="OpenEMR Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://veris-teal.vercel.app",
        "http://localhost:3000",
        "http://localhost:8300",
        "https://localhost:9300",
        "https://openemr-production-7df2.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    thread_id: str


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    tools_used: list[str] = []
    trace_id: str = ""
    confidence_score: float = 1.0
    requires_escalation: bool = False  # True when confidence < 0.6 — signals human review


class FeedbackRequest(BaseModel):
    trace_id: str
    score: int  # 1 = positive, 0 = negative
    comment: str | None = None


class FeedbackResponse(BaseModel):
    success: bool
    trace_id: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    thread_id = req.thread_id or uuid.uuid4().hex
    result = await run_agent(req.message, thread_id=thread_id)
    confidence_score = result.get("confidence_score", 1.0)
    return ChatResponse(
        response=result["response"],
        thread_id=thread_id,
        tools_used=result["tools_used"],
        trace_id=result.get("trace_id", ""),
        confidence_score=confidence_score,
        requires_escalation=confidence_score < 0.6,
    )


@app.post("/feedback", response_model=FeedbackResponse)
async def feedback(req: FeedbackRequest):
    if req.score not in (0, 1):
        raise HTTPException(status_code=422, detail="score must be 0 or 1")
    success = log_feedback(
        trace_id=req.trace_id,
        score=req.score,
        comment=req.comment,
    )
    return FeedbackResponse(success=success, trace_id=req.trace_id)


@app.get("/health")
async def health():
    openemr_connected = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OPENEMR_BASE_URL}/apis/default/fhir/metadata")
            openemr_connected = resp.status_code == 200
    except Exception:
        pass
    return {"status": "healthy", "openemr_connected": openemr_connected}
