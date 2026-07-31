"""The interview brain — a lifelike 3-part mock interview.

Part 1 (Technical): blends the candidate's real resume work with core fundamentals.
Part 2 (Coding): one problem, answered in pseudocode.
Part 3 (Behavioral): what kind of person the candidate is.

It runs as one natural conversation: the interviewer reacts to answers and follows up, never
announces which topic it's asking about, and grounds questions in the resume when one is given.
The number of questions in the technical and behavioral parts is randomized per session; the
coding part is always exactly one problem.
"""
from __future__ import annotations

import json
import random
import time
import uuid

from .config import MODEL, get_client

SYSTEM = (
    "You are an experienced, personable interviewer conducting a realistic mock interview for a "
    "{role} role. Behave like a real human interviewer, NOT a quiz bot.\n"
    "How to behave:\n"
    "- Have a natural conversation. React briefly to what the candidate says, then ask your next "
    "question. FOLLOW UP on their answers — if they mention a project, a decision, or something "
    "incomplete or interesting, dig into THAT before moving on.\n"
    "- NEVER announce topics or transitions. Do NOT say things like 'let's move on to DBMS', 'now "
    "an OS question', or name the subject area you're testing. Just ask the question naturally.\n"
    "- Do NOT march through concepts one-question-per-topic like a checklist. Let the conversation flow.\n"
    "- Ask ONE question at a time, and keep it concise.\n"
    "- If an answer is vague, shallow, or evasive, press for specifics before moving on.\n"
    "- When a resume is provided, ground many of your questions in the candidate's REAL projects, "
    "skills, and decisions — ask them to go deep on what they've actually built.\n"
    "- Stay professional. Do NOT give feedback or scores during the interview."
)

ROUNDS = [
    {"key": "technical", "name": "Technical", "seconds": 120, "instruction": (
        "For this part, probe the candidate's TECHNICAL depth. Blend questions about their actual "
        "resume projects and decisions with core fundamentals (OOP, DBMS, networking, operating "
        "systems, DSA, and concepts central to the {role} role). Move fluidly between their real "
        "experience and the underlying theory, and follow up on what they say. "
        "IMPORTANT: regardless of how project-focused the candidate's answers are, make sure at least "
        "THREE questions in this part test pure fundamentals (OOP, DBMS, operating systems, "
        "networking, or DSA) — not tied to their resume."
    )},
    {"key": "coding", "name": "Coding", "seconds": 300, "instruction": (
        "Now give the candidate ONE coding problem suitable for a {role}. Introduce it naturally "
        "(for example: \"Let's try a quick coding problem\") and ask them to write PSEUDOCODE for "
        "their approach — not full, runnable code."
    )},
    {"key": "behavioral", "name": "Behavioral", "seconds": 120, "instruction": (
        "Now shift naturally into understanding the candidate as a person — how they work in a team, "
        "handle conflict, deal with failure or pressure, and what motivates them. Draw on real "
        "experiences from their resume where you can. No technical questions here."
    )},
]

TOTAL_ROUNDS = len(ROUNDS)

# In-memory session store: session_id -> {messages, answered, role, counts}.
_sessions: dict[str, dict] = {}


def _pick_counts() -> list[int]:
    """Randomize how many questions each part gets. Coding is always exactly one problem."""
    return [random.randint(4, 7), 1, random.randint(3, 5)]


def _round_of(idx: int, counts: list[int]):
    """Which part does the (0-based) question index fall in? Returns (index, round, is_first)."""
    c = 0
    for i, n in enumerate(counts):
        if idx < c + n:
            return i, ROUNDS[i], (idx == c)
        c += n
    return None, None, False


def _session_lean(role: str) -> str:
    """Pick a couple of areas to lean toward this session, for variety — without forcing an order."""
    areas = [
        "object-oriented programming", "databases and SQL", "computer networks",
        "operating systems", "data structures and algorithms",
        f"the core of the {role} role", "their resume projects",
    ]
    random.shuffle(areas)
    return (f" Lean a little more toward {areas[0]} and {areas[1]} this session, "
            "but let the candidate's answers guide where you go.")


def _system_prompt(role: str, resume: str) -> str:
    base = SYSTEM.format(role=role)
    if resume.strip():
        base += (
            "\n\nThe candidate's RESUME is below — treat it as central to the interview. Ask them to "
            "go deep on their real projects, skills, and decisions from it throughout.\n"
            "--- RESUME ---\n" + resume.strip()[:4000] + "\n--- END RESUME ---"
        )
    return base


def _round_instruction(round_dict: dict, role: str, first_overall: bool) -> str:
    instr = round_dict["instruction"].format(role=role)
    if round_dict["key"] == "technical":
        instr += _session_lean(role)
    if first_overall:
        instr += (
            " Open with a brief, warm one-line greeting. Then, if a resume is available, make your "
            "first question about a specific project or skill from it; otherwise, ask the candidate "
            "to briefly introduce themselves."
        )
    return instr


def _complete(**kwargs):
    from groq import RateLimitError
    last_err = None
    for attempt in range(3):
        try:
            return get_client().chat.completions.create(**kwargs)
        except RateLimitError as exc:  # hard limit — retrying won't help, fail fast with a clear message
            raise RuntimeError(
                "The free AI rate limit was reached (daily token cap). Please wait a few minutes "
                "and try again, or add your own API key with a higher limit."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - transient network blip, retry
            last_err = exc
            time.sleep(0.7 * (attempt + 1))
    raise last_err


def _ask_model(messages: list[dict]) -> str:
    # Higher temperature = more variety between sessions.
    resp = _complete(model=MODEL, messages=messages, temperature=0.95, max_tokens=350)
    return resp.choices[0].message.content.strip()


def start(role: str, resume: str = "") -> tuple:
    """Begin the interview. Returns (session_id, question, seconds, total_q, round_name, round_index)."""
    counts = _pick_counts()
    messages = [{"role": "system", "content": _system_prompt(role, resume)}]
    r = ROUNDS[0]
    messages.append({"role": "system", "content": _round_instruction(r, role, first_overall=True)})
    question = _ask_model(messages)
    messages.append({"role": "assistant", "content": question})

    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"messages": messages, "answered": 0, "role": role, "counts": counts}
    return session_id, question, r["seconds"], sum(counts), r["name"], 1


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
    counts = session["counts"]

    if n >= sum(counts):
        session["messages"].append({
            "role": "system",
            "content": "That was the final question. Warmly thank the candidate in 1-2 sentences and "
                       "tell them to request their report. Do not ask another question.",
        })
        reply = _ask_model(session["messages"])
        session["messages"].append({"role": "assistant", "content": reply})
        return reply, True, n, 0, ROUNDS[-1]["name"], TOTAL_ROUNDS

    round_i, r, is_first = _round_of(n, counts)  # next question is index n
    if is_first:
        session["messages"].append({"role": "system", "content": _round_instruction(r, role, first_overall=False)})

    reply = _ask_model(session["messages"])
    session["messages"].append({"role": "assistant", "content": reply})
    return reply, False, n, r["seconds"], r["name"], round_i + 1


_FEEDBACK_SYSTEM = (
    "You are an expert interview coach. You are given a transcript of a 3-part mock interview "
    "(Technical, Coding/pseudocode, Behavioral). Evaluate ONLY the candidate's answers, fairly and "
    "constructively. Return strict JSON with this exact shape:\n"
    "{\n"
    '  "overall_score": <integer 1-10>,\n'
    '  "summary": "<2-3 sentence overall assessment>",\n'
    '  "rounds": [\n'
    '    {"name": "Technical", "score": <1-10>, "note": "<short note>"},\n'
    '    {"name": "Coding", "score": <1-10>, "note": "<short note>"},\n'
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
    """Score the completed interview and return a structured report."""
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
