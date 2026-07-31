"""FastAPI entrypoint — the interview API.

Try it live in the auto-generated docs at http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import interview
from .schemas import (
    AnswerRequest,
    AnswerResponse,
    FeedbackRequest,
    StartRequest,
    StartResponse,
)

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
        session_id, question, seconds, total, round_name, round_i = interview.start(req.role, req.resume)
    except RuntimeError as exc:  # missing API key
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # model/network error
        raise HTTPException(status_code=502, detail=f"Interview failed to start: {exc}")
    return StartResponse(
        session_id=session_id, question=question, seconds=seconds, total_questions=total,
        total_rounds=interview.TOTAL_ROUNDS, round=round_name, round_index=round_i,
    )


@app.post("/api/interview/answer", response_model=AnswerResponse)
def answer(req: AnswerRequest) -> AnswerResponse:
    """Submit an answer; get the interviewer's adaptive follow-up or next question."""
    try:
        message, done, n, seconds, round_name, round_i = interview.answer(req.session_id, req.answer)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found — start a new interview.")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not process answer: {exc}")
    return AnswerResponse(
        message=message, done=done, question_number=n, seconds=seconds,
        round=round_name, round_index=round_i,
    )


@app.post("/api/interview/feedback")
def feedback(req: FeedbackRequest) -> dict:
    """Score the completed interview and return structured, actionable feedback."""
    try:
        return interview.feedback(req.session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found — start a new interview.")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not generate feedback: {exc}")
