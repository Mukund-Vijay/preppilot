"""FastAPI entrypoint — the interview API.

Try it live in the auto-generated docs at http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import interview, resume as resume_mod
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


@app.post("/api/resume/extract")
async def extract_resume(file: UploadFile = File(...)) -> dict:
    """Read an uploaded resume (PDF/DOCX/TXT) and return its extracted text."""
    data = await file.read()
    if len(data) > 5_000_000:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB).")
    try:
        text = resume_mod.extract_text(file.filename or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not read the file: {exc}")
    if not text.strip():
        raise HTTPException(status_code=422,
                            detail="No text found — if it's a scanned PDF, paste the text instead.")
    return {"text": text[:8000], "filename": file.filename}


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
