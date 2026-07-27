# PrepPilot

An AI mock-interviewer that asks you real interview questions, **adapts with follow-up
questions based on your answers** (like a real interviewer digging in), and gives you
scored, actionable feedback.

Not a static question list — a stateful conversation with an evaluation rubric.

## Build roadmap

- [x] **Phase 1 — Backend brain.** FastAPI endpoint that runs an adaptive behavioral
      interview via an LLM, maintaining conversation state for follow-up questions.
- [x] **Phase 2 — Feedback rubric.** Structured scoring (communication, structure/STAR, specificity).
- [x] **Phase 3 — React chat UI.** A full setup → interview → feedback interface.
- [ ] **Phase 4 — Progress tracking.** Save sessions + weak areas (SQLite).
- [ ] **Phase 5 — Wow upgrades.** Voice input · job-description-tailored questions.

## Quick start

```bash
# 1. Backend (needs a free GROQ_API_KEY in backend/.env)
cd backend
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# 2. Frontend (in a second terminal)
cd frontend
npm install
npm run dev                   # opens http://localhost:5174
```

## Stack

- **Backend:** Python · FastAPI · session-based REST API
- **AI:** Groq LLM (free tier) — swappable
- **Frontend:** React + Vite

## Status

Phases 1–3 complete — working end to end (adaptive interview + scored feedback).
