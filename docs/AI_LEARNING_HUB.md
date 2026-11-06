# AI Learning Hub

A personalised, AI-driven learning ecosystem inside ARJUNA AI. **Gemini writes the learning content; the application provides the framework, scheduling, scoring and tracking.** No notes, quizzes or roadmaps are hardcoded.

## What is (and is not) seeded
Seeded reference data only (`python -m app.seeds.learning_seed`): 20 career tracks, 249 topics, topic prerequisites (`app/data/learning_tracks.py`). The optional `learning_resources` table is empty and is for *manually verified* links only. Everything a learner sees (plans, notes, quizzes, summaries) is generated on request and stored per user.

## Setup
```bash
cd backend
pip install -r requirements.txt
python -m alembic upgrade head
python -m app.seeds.learning_seed
```
Environment (backend `.env`, never the frontend): `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-flash-lite-latest`), optional `GEMINI_FALLBACK_MODELS` (tried in order on 429/500/503/404).

## Architecture (`backend/app/modules/learning/`)
| Module | Role |
|---|---|
| `ai.py` | Prompts + pydantic response schemas (lenient to list/string slips). Forbids invented URLs, stats, citations. |
| `skill_gap.py` | TF-IDF + token overlap between the learner's *existing* profile and a track. Gemini only explains it. |
| `planner.py` | Generates a plan: Gemini produces study units per phase; the scheduler places them. Regeneration, missed-work redistribution, adaptive workload advice. |
| `scheduler.py` | Pure, tested calendar logic: study/rest dates, daily budgets, reserved revision/assessment/final days, packing, redistribution. |
| `materials.py` / `youtube.py` | On-demand notes (+simplify/deeper/examples/implementation/diagram/follow-up); YouTube metadata (oEmbed) + captions, with pasted-transcript fallback. |
| `notebooks.py` | Notebooks, chapters, pages, history, search, imports (PDF/DOCX/TXT), server-side lock. |
| `quizzes.py` / `evaluation.py` | Question generation and validation; deterministic scoring; sandboxed code tests; rubric-graded written answers. |
| `mastery.py` / `mastery_service.py` / `srs.py` / `revision.py` | Multi-signal mastery; SM-2 spaced repetition with adjustable intervals; automatic revision tasks. |
| `analytics.py` | Overview, progress, explainable rule-based recommendations, personalisation status. |
| `events.py` | Append-only learning event log + explicit feedback signals. |

API: 58 authenticated endpoints under `/api/learning/*` (see `/docs`). Every route requires the existing JWT session and is scoped to the caller.

## Design decisions worth knowing
* **Realistic workloads are guaranteed by code, not by the model.** Gemini returns units with minute estimates; `scheduler.place_all` packs them (shrinking durations if whole units cannot share a day) so no day exceeds the learner's budget and nothing is silently dropped.
* **Generation is all-or-nothing.** If any phase fails to generate/validate, nothing is saved.
* **Mastery** uses quiz evidence only (difficulty- and recency-weighted accuracy, subtopic coverage, coding results, SRS retention, improvement). Opening notes or watching videos never raises it. Statuses: Not started, Learning, Developing, Needs revision, Strong, Mastered.
* **Coding questions** must ship with a reference solution; the server runs it against the question's own test cases and drops the question if it fails.
* **Missed work** is previewed first; significant changes need explicit confirmation.

## Security & privacy
* **Notebook lock** = server-side access control. Pages, index and search return `423 Locked` without a short-lived (30 min) signed token, issued only after the Argon2 password check. Tokens are bound to the user and notebook and are not valid session tokens. Unlock attempts are rate-limited. This is **not end-to-end encryption**: page text is stored unencrypted, and there is **no password recovery**.
* **Code sandbox** (`evaluation.run_sandboxed`): separate interpreter (`-I`), empty environment, scratch directory, import allow-list, stripped builtins, audit-hook deny list (files, sockets, subprocesses), hard timeout. **It is defence in depth, not a hostile multi-tenant sandbox.** Before exposing this publicly, run it inside a container/gVisor with CPU, memory and network limits.
* AI endpoints are rate-limited per user. API keys never reach the browser.

## Personalisation roadmap
Today: transparent rules and statistics (TF-IDF, cosine similarity, weighted scoring, SM-2). Every recommendation states its reason, and learners can rate it. All behaviour is logged (`learning_events`, `personalization_feedback`). A contextual bandit, and later RL, should only be enabled once enough real interaction data exists (`/learning/personalization` reports readiness; threshold ~1,500 events) and should optimise retention, assessment gains, consistency and sustainable workload, never time-in-app. No model is trained or claimed today.

## Known limitations
* Plan generation takes roughly 20-90 seconds (several Gemini calls); the UI shows progress.
* YouTube captions depend on the uploader and on YouTube not blocking the server; the pasted-transcript path always works.
* Resource suggestions are search suggestions written by AI, shown as unverified.
* Rubric grading depends on Gemini availability; ungradable answers are excluded from scores and mastery rather than scored zero.

## Tests
`backend/tests/test_learning_logic.py` (pure logic: scheduler, SRS, mastery, scoring, sandbox, seed parsing, URL parsing) and `backend/tests/test_learning_api.py` (integration against the real app and database with Gemini stubbed in tests only).
```bash
cd backend && python -m pytest tests -q
```
