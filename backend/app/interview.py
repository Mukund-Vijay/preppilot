"""The interview brain.

Key idea: an interview is a *conversation*, so we keep the full message history for each
session and feed it back to the model every turn. Because the model sees the candidate's
previous answers, it can ask adaptive follow-ups — the thing that makes this feel real.
"""
from __future__ import annotations

import json
import uuid

from .config import MODEL, get_client

MAX_QUESTIONS = 5

# In-memory session store: session_id -> {messages, count, role}.
# (Simple for now. In Phase 4 we'll swap this for a database so progress survives restarts.)
_sessions: dict[str, dict] = {}


def _system_prompt(role: str) -> str:
    """The 'character' and rules we give the model — this shapes the whole interview."""
    return (
        f"You are a professional interviewer conducting a realistic, lightly pressured mock "
        f"interview for a {role} role. Keep the tone crisp and professional, like a real interview.\n"
        "Rules:\n"
        "- Your FIRST message must open with a one-line professional greeting and then ask the "
        "candidate to introduce themselves (a natural 'Tell me about yourself').\n"
        "- Ask ONE question at a time, concise (1-2 sentences).\n"
        "- If an answer is vague, generic, evasive, or too short, DO NOT let it slide: press the "
        "candidate for specifics — a concrete example, their exact actions, or numbers — before "
        "moving on.\n"
        "- If an answer is solid, ask a natural follow-up that digs deeper, then advance to a new question.\n"
        "- Stay neutral and professional; do NOT give praise, feedback, or scores during the interview."
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


_FEEDBACK_SYSTEM = (
    "You are an expert interview coach. You are given a transcript of a mock behavioral "
    "interview. Evaluate ONLY the candidate's answers, fairly and constructively. "
    "Return strict JSON with this exact shape:\n"
    "{\n"
    '  "overall_score": <integer 1-10>,\n'
    '  "summary": "<2-3 sentence overall assessment>",\n'
    '  "strengths": ["<point>", "<point>"],\n'
    '  "improvements": ["<actionable tip>", "<actionable tip>"],\n'
    '  "dimensions": [\n'
    '    {"name": "Communication", "score": <1-10>, "note": "<short note>"},\n'
    '    {"name": "Structure (STAR)", "score": <1-10>, "note": "<short note>"},\n'
    '    {"name": "Specificity", "score": <1-10>, "note": "<short note>"}\n'
    "  ]\n"
    "}\n"
    "Be honest but encouraging. Give concrete, specific advice a student can act on."
)


def _transcript(messages: list[dict]) -> str:
    """Render the conversation as a plain Interviewer/Candidate transcript for scoring."""
    lines = []
    for m in messages:
        if m["role"] == "assistant":
            lines.append(f"Interviewer: {m['content']}")
        elif m["role"] == "user":
            lines.append(f"Candidate: {m['content']}")
    return "\n".join(lines)


def feedback(session_id: str) -> dict:
    """Score a completed interview and return structured, actionable feedback."""
    session = _sessions.get(session_id)
    if session is None:
        raise KeyError("session not found")

    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _FEEDBACK_SYSTEM},
            {"role": "user", "content": "Transcript:\n\n" + _transcript(session["messages"])},
        ],
        temperature=0.3,
        max_tokens=800,
        response_format={"type": "json_object"},  # force valid JSON
    )
    return json.loads(resp.choices[0].message.content)
