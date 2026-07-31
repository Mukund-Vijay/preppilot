"""The interview brain — a structured 3-round mock interview.

Round 1: Technical theory (OOP, DBMS, Networking, OS, DSA + role core)
Round 2: Coding — the candidate writes pseudocode for a problem
Round 3: Behavioral — what kind of person the candidate is

It's one continuous conversation with the model; we steer it round-by-round by injecting a
system instruction at each round boundary, and we report on all three rounds at the end.
"""
from __future__ import annotations

import json
import time
import uuid

from .config import MODEL, get_client

ROUNDS = [
    {
        "key": "technical",
        "name": "Technical — Theory",
        "q": 4,
        "seconds": 120,
        "instruction": (
            "ROUND 1 of 3 — TECHNICAL THEORY. Ask concise conceptual theory questions (NO coding "
            "problems in this round). Draw from Object-Oriented Programming, DBMS, Computer Networks, "
            "Operating Systems, and Data Structures & Algorithms, plus core concepts specific to the "
            "{role} role. One concept per question."
        ),
    },
    {
        "key": "coding",
        "name": "Coding — Pseudocode",
        "q": 2,
        "seconds": 240,
        "instruction": (
            "ROUND 2 of 3 — CODING. Pose ONE clear, self-contained coding problem suitable for a "
            "{role} and explicitly ask the candidate to write PSEUDOCODE for their approach (not full, "
            "runnable code). After they answer, ask exactly ONE follow-up about time/space complexity "
            "or edge cases, then the round ends."
        ),
    },
    {
        "key": "behavioral",
        "name": "Behavioral",
        "q": 3,
        "seconds": 90,
        "instruction": (
            "ROUND 3 of 3 — BEHAVIORAL. Ask questions to understand what kind of person the candidate "
            "is: how they work in a team, handle conflict, deal with failure or pressure, and what "
            "motivates them. NO technical questions in this round."
        ),
    },
]

TOTAL_Q = sum(r["q"] for r in ROUNDS)
TOTAL_ROUNDS = len(ROUNDS)

# In-memory session store: session_id -> {messages, answered, role}.
_sessions: dict[str, dict] = {}


def _round_of(idx: int):
    """Which round does the (0-based) question index fall in? Returns (round_index, round, is_first)."""
    c = 0
    for i, r in enumerate(ROUNDS):
        if idx < c + r["q"]:
            return i, r, (idx == c)
        c += r["q"]
    return None, None, False


def _system_prompt(role: str, resume: str) -> str:
    base = (
        f"You are a professional interviewer running a structured 3-round mock interview for a {role} "
        "role: Round 1 technical theory, Round 2 a coding/pseudocode question, Round 3 behavioral.\n"
        "Rules:\n"
        "- Ask ONE question at a time. Keep it concise (a coding problem may be a little longer).\n"
        "- Follow the ROUND instruction you are given for what to ask next.\n"
        "- If an answer is vague, generic, or too short, press once for specifics before moving on.\n"
        "- Stay professional. Do NOT give feedback or scores during the interview."
    )
    if resume.strip():
        base += (
            "\n\nCandidate resume — tailor questions to their real experience where relevant:\n"
            "--- RESUME ---\n" + resume.strip()[:4000] + "\n--- END RESUME ---"
        )
    return base


def _round_instruction(round_dict: dict, role: str, first_overall: bool) -> str:
    instr = round_dict["instruction"].format(role=role)
    if first_overall:
        return instr + " Begin with a one-line professional greeting, then ask your first question."
    return (
        "The previous round is complete. " + instr +
        " Start with a one-line transition announcing this new round, then ask your first question."
    )


def _complete(**kwargs):
    """Call Groq with a few retries so a transient network blip doesn't surface as an error."""
    last_err = None
    for attempt in range(3):
        try:
            return get_client().chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(0.7 * (attempt + 1))
    raise last_err


def _ask_model(messages: list[dict]) -> str:
    resp = _complete(model=MODEL, messages=messages, temperature=0.7, max_tokens=350)
    return resp.choices[0].message.content.strip()


def start(role: str, resume: str = "") -> tuple:
    """Begin the interview. Returns (session_id, question, seconds, total_q, round_name, round_index)."""
    messages = [{"role": "system", "content": _system_prompt(role, resume)}]
    r = ROUNDS[0]
    messages.append({"role": "system", "content": _round_instruction(r, role, first_overall=True)})
    question = _ask_model(messages)
    messages.append({"role": "assistant", "content": question})

    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"messages": messages, "answered": 0, "role": role}
    return session_id, question, r["seconds"], TOTAL_Q, r["name"], 1


def answer(session_id: str, user_answer: str) -> tuple:
    """Record an answer and get the next line.

    Returns (message, done, question_number, seconds, round_name, round_index).
    """
    session = _sessions.get(session_id)
    if session is None:
        raise KeyError("session not found")

    session["messages"].append({"role": "user", "content": user_answer})
    session["answered"] += 1
    n = session["answered"]
    role = session["role"]

    if n >= TOTAL_Q:
        session["messages"].append({
            "role": "system",
            "content": "That was the final question. Warmly thank the candidate in 1-2 sentences and "
                       "tell them to request their report. Do not ask another question.",
        })
        reply = _ask_model(session["messages"])
        session["messages"].append({"role": "assistant", "content": reply})
        return reply, True, n, 0, ROUNDS[-1]["name"], TOTAL_ROUNDS

    round_i, r, is_first = _round_of(n)  # the next question is index n
    if is_first:
        session["messages"].append({"role": "system", "content": _round_instruction(r, role, first_overall=False)})

    reply = _ask_model(session["messages"])
    session["messages"].append({"role": "assistant", "content": reply})
    return reply, False, n, r["seconds"], r["name"], round_i + 1


_FEEDBACK_SYSTEM = (
    "You are an expert interview coach. You are given a transcript of a 3-round mock interview "
    "(Round 1 Technical theory, Round 2 Coding/pseudocode, Round 3 Behavioral). Evaluate ONLY the "
    "candidate's answers, fairly and constructively. Return strict JSON with this exact shape:\n"
    "{\n"
    '  "overall_score": <integer 1-10>,\n'
    '  "summary": "<2-3 sentence overall assessment>",\n'
    '  "rounds": [\n'
    '    {"name": "Technical — Theory", "score": <1-10>, "note": "<short note>"},\n'
    '    {"name": "Coding — Pseudocode", "score": <1-10>, "note": "<short note>"},\n'
    '    {"name": "Behavioral", "score": <1-10>, "note": "<short note>"}\n'
    "  ],\n"
    '  "strengths": ["<point>", "<point>"],\n'
    '  "improvements": ["<actionable tip>", "<actionable tip>"]\n'
    "}\n"
    "Be honest but encouraging. Give concrete, specific advice a student can act on."
)


def _transcript(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        if m["role"] == "assistant":
            lines.append(f"Interviewer: {m['content']}")
        elif m["role"] == "user":
            lines.append(f"Candidate: {m['content']}")
    return "\n".join(lines)


def feedback(session_id: str) -> dict:
    """Score the completed 3-round interview and return a structured report."""
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
        max_tokens=900,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)
