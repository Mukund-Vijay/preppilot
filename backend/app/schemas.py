"""Request/response models (Pydantic v2)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    role: str = Field("Software Engineer", description="Role you're interviewing for")
    resume: str = ""  # optional: paste resume text to get tailored questions


class StartResponse(BaseModel):
    session_id: str
    question: str
    seconds: int          # time budget for this question
    total_questions: int
    total_rounds: int
    round: str            # current round name
    round_index: int      # 1-based


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


class AnswerResponse(BaseModel):
    message: str
    done: bool
    question_number: int
    seconds: int          # time budget for the NEXT question (0 when done)
    round: str
    round_index: int


class FeedbackRequest(BaseModel):
    session_id: str
