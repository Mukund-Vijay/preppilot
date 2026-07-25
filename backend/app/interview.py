"""The interview brain.

Key idea: an interview is a *conversation*, so we keep the full message history for each
session and feed it back to the model every turn. Because the model sees the candidate's
previous answers, it can ask adaptive follow-ups — the thing that makes this feel real.
"""
from __future__ import annotations

import uuid

from .config import MODEL, get_client

MAX_QUESTIONS = 5

# In-memory session store: session_id -> {messages, count, role}.
# (Simple for now. In Phase 4 we'll swap this for a database so progress survives restarts.)
_sessions: dict[str, dict] = {}


def _system_prompt(role: str) -> str:
    """The 'character' and rules we give the model — this shapes the whole interview."""
    return (
        f"You are a warm but sharp interviewer running a BEHAVIORAL interview for a {role} role.\n"
        "Rules:\n"
        "- Ask ONE question at a time, 1-2 sentences max.\n"
        "- After each answer, either ask a natural FOLLOW-UP that digs into what they "
        "actually said (like a real interviewer probing deeper), or move to a fresh "
        "behavioral question. Prefer follow-ups when an answer is vague.\n"
        "- Do NOT give feedback or scores during the interview — just interview.\n"
        "- Open with a one-line friendly intro, then your first question."
    )


def _ask_model(messages: list[dict]) -> str:
    """Send the conversation to Groq and return the model's reply text."""
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=250,
    )
    return resp.choices[0].message.content.strip()


def start(role: str) -> tuple[str, str]:
    """Begin a new interview. Returns (session_id, first_question)."""
    messages = [{"role": "system", "content": _system_prompt(role)}]
    question = _ask_model(messages)
    messages.append({"role": "assistant", "content": question})

    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"messages": messages, "count": 0, "role": role}
    return session_id, question


def answer(session_id: str, user_answer: str) -> tuple[str, bool, int]:
    """Record the candidate's answer and get the interviewer's next line.

    Returns (interviewer_message, done, question_number).
    """
    session = _sessions.get(session_id)
    if session is None:
        raise KeyError("session not found")

    session["messages"].append({"role": "user", "content": user_answer})
    session["count"] += 1
    done = session["count"] >= MAX_QUESTIONS

    if done:
        # Nudge the model to wrap up gracefully instead of asking more.
        session["messages"].append({
            "role": "system",
            "content": "That was the final answer. Warmly thank the candidate in 1-2 "
                       "sentences and tell them to request feedback. Do not ask another question.",
        })

    reply = _ask_model(session["messages"])
    session["messages"].append({"role": "assistant", "content": reply})
    return reply, done, session["count"]
