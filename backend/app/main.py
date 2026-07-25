"""FastAPI entrypoint — the interview API.

Try it live in the auto-generated docs at http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import interview
from .schemas import AnswerRequest, AnswerResponse, StartRequest, StartResponse

app = FastAPI(title="PrepPilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/interview/start", response_model=StartResponse)
def start(req: StartRequest) -> StartResponse:
    """Begin an interview for a role. Returns a session_id + the first question."""
    try:
        session_id, question = interview.start(req.role)
    except RuntimeError as exc:  # missing API key
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # model/network error
        raise HTTPException(status_code=502, detail=f"Interview failed to start: {exc}")
    return StartResponse(session_id=session_id, question=question)


@app.post("/api/interview/answer", response_model=AnswerResponse)
def answer(req: AnswerRequest) -> AnswerResponse:
    """Submit an answer; get the interviewer's adaptive follow-up or next question."""
    try:
        message, done, n = interview.answer(req.session_id, req.answer)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found — start a new interview.")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not process answer: {exc}")
    return AnswerResponse(message=message, done=done, question_number=n)
