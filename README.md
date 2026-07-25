# PrepPilot

An AI mock-interviewer that asks you real interview questions, **adapts with follow-up
questions based on your answers** (like a real interviewer digging in), and gives you
scored, actionable feedback.

Not a static question list — a stateful conversation with an evaluation rubric.

## Build roadmap

- [ ] **Phase 1 — Backend brain (API only).** FastAPI endpoint that runs an adaptive
      behavioral interview via an LLM, tested in the auto-generated `/docs` page.
- [ ] **Phase 2 — Feedback rubric.** Structured scoring (clarity, structure/STAR, specifics).
- [ ] **Phase 3 — React chat UI.** A proper interview interface.
- [ ] **Phase 4 — Progress tracking.** Save sessions + weak areas (SQLite).
- [ ] **Phase 5 — Wow upgrades.** Voice input · job-description-tailored questions.

## Stack

- **Backend:** Python · FastAPI
- **AI:** Groq (free tier, no credit card) — swappable
- **Frontend:** React + Vite (Phase 3)

## Status

Phase 1 in progress.
