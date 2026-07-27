"""Request/response shapes for the API (Pydantic validates these automatically)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    role: str = Field("Software Engineer", description="Role you're interviewing for")


class StartResponse(BaseModel):
    session_id: str
    question: str


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


class AnswerResponse(BaseModel):
    message: str          # the interviewer's next line (follow-up or new question)
    done: bool            # True once the interview is over
    question_number: int  # how many questions you've answered so far


class FeedbackRequest(BaseModel):
    session_id: str
