"""Loads settings from .env and hands out a configured Groq client."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # reads backend/.env into environment variables

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Which model to use. Groq is free and fast. Override in .env if you like.
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_client() -> Groq:
    """Return a ready-to-use Groq client, or a clear error if the key is missing."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing — add it to backend/.env")
    return Groq(api_key=GROQ_API_KEY)
