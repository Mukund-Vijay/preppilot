"""The interview brain.

An interview is a *conversation*, so we keep the full message history per session and feed
it back to the model each turn — that's what lets it ask adaptive follow-ups. The mode,
optional resume, and per-question time budgets are all injected here.
"""
from __future__ import annotations

import json
import time
import uuid

from .config import MODEL, get_client

MAX_QUESTIONS = 8

# Per-question time budgets (seconds), indexed by question number. Varying the time by
# question type makes the interview feel real instead of a rigid fixed clock — technical
# questions get more thinking time, the intro gets a little extra, etc.
TIME_PLANS = {
    "behavioral": [120, 90, 100, 90, 110, 90, 100, 90],
    "technical": [120, 150, 180, 150, 170, 150, 180, 160],
    "mixed": [120, 90, 150, 100, 160, 90, 150, 110],
}

_MODE_RULES = {
    "behavioral": (
        "Run a BEHAVIORAL interview: focus on past experiences, teamwork, conflict, ownership, "
        "and how they handled real situations."
    ),
    "technical": (
        "Run a TECHNICAL interview for this role: ask about core concepts, trade-offs, debugging "
        "approaches, and how they would design or reason through problems. Ask them to explain "
        "their thinking out loud. Do NOT require them to write or run actual code."
    ),
    "mixed": (
        "Run a realistic MIXED interview: after the introduction, alternate between behavioral "
        "questions and technical questions relevant to the role, and dig into their background."
    ),
}

# In-memory session store: session_id -> {messages, count, role, mode}.
_sessions: dict[str, dict] = {}


def _seconds_for(mode: str, index: int) -> int:
    plan = TIME_PLANS.get(mode, TIME_PLANS["mixed"])
    return plan[min(index, len(plan) - 1)]


def _system_prompt(role: str, mode: str, resume: str) -> str:
    """The 'character' and rules for the interviewer — mode + resume shape the whole session."""
    base = (
        f"You are a professional interviewer conducting a realistic, lightly pressured mock "
        f"interview for a {role} role. Keep the tone crisp and professional.\n"
        f"{_MODE_RULES.get(mode, _MODE_RULES['mixed'])}\n"
        "Rules:\n"
        "- Your FIRST message: a one-line professional greeting, then ask the candidate to "
        "introduce themselves ('Tell me about yourself').\n"
        "- Ask ONE question at a time, concise (1-2 sentences).\n"
        "- If an answer is vague, generic, evasive, or too short, DO NOT let it slide: press the "
        "candidate for specifics — a concrete example, their exact actions, or numbers — before "
        "moving on.\n"
        "- If an answer is solid, ask a natural follow-up that digs deeper, then advance to a new question.\n"
        "- Stay neutral and professional; do NOT give praise, feedback, or scores during the interview."
    )
    if resume.strip():
        base += (
            "\n\nThe candidate's resume is below. Ask several questions grounded in their ACTUAL "
            "projects, experience, and skills from it (e.g., 'You built X — walk me through the "
            "hardest technical decision you made').\n"
            "--- RESUME ---\n" + resume.strip()[:4000] + "\n--- END RESUME ---"
        )
    return base


def _complete(**kwargs):
    """Call Groq with a few extra retries (on top of the SDK's) so a transient network
    blip during an interview doesn't surface as an error to the user."""
    last_err = None
    for attempt in range(3):
        try:
            return get_client().chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - retry any transient failure
            last_err = exc
            time.sleep(0.7 * (attempt + 1))
    raise last_err


def _ask_model(messages: list[dict]) -> str:
    """Send the conversation to Groq and return the model's reply text."""
    resp = _complete(model=MODEL, messages=messages, temperature=0.7, max_tokens=250)
    return resp.choices[0].message.content.strip()


def start(role: str, mode: str = "mixed", resume: str = "") -> tuple[str, str, int, int]:
    """Begin an interview. Returns (session_id, first_question, seconds, total_questions)."""
    messages = [{"role": "system", "content": _system_prompt(role, mode, resume)}]
    question = _ask_model(messages)
    messages.append({"role": "assistant", "content": question})

    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"messages": messages, "count": 0, "role": role, "mode": mode}
    return session_id, question, _seconds_for(mode, 0), MAX_QUESTIONS


def answer(session_id: str, user_answer: str) -> tuple[str, bool, int, int]:
    """Record the answer and get the interviewer's next line.

    Returns (interviewer_message, done, question_number, seconds_for_next_question).
    """
    session = _sessions.get(session_id)
    if session is None:
        raise KeyError("session not found")

    session["messages"].append({"role": "user", "content": user_answer})
    session["count"] += 1
    n = session["count"]
    done = n >= MAX_QUESTIONS

    if done:
        session["messages"].append({
            "role": "system",
            "content": "That was the final answer. Warmly thank the candidate in 1-2 sentences "
                       "and tell them to request feedback. Do not ask another question.",
        })

    reply = _ask_model(session["messages"])
    session["messages"].append({"role": "assistant", "content": reply})
    seconds = 0 if done else _seconds_for(session.get("mode", "mixed"), n)
    return reply, done, n, seconds


_FEEDBACK_SYSTEM = (
    "You are an expert interview coach. You are given a transcript of a mock interview. "
    "Evaluate ONLY the candidate's answers, fairly and constructively. "
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

    resp = _complete(
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
