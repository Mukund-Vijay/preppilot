"""Request/response shapes for the API (Pydantic validates these automatically)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    role: str = Field("Software Engineer", description="Role you're interviewing for")
    mode: Literal["behavioral", "technical", "mixed"] = "mixed"
    resume: str = ""  # optional: paste resume text to get tailored questions


class StartResponse(BaseModel):
    session_id: str
    question: str
    seconds: int          # time budget for this question
    total_questions: int  # how many questions the interview will have


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


class AnswerResponse(BaseModel):
    message: str          # the interviewer's next line (follow-up or new question)
    done: bool            # True once the interview is over
    question_number: int  # how many questions you've answered so far
    seconds: int          # time budget for the NEXT question (0 when done)


class FeedbackRequest(BaseModel):
    session_id: str
