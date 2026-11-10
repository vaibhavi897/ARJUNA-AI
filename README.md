# ARJUNA AI — Autonomous Readiness, Job-fit & Unified Navigational Architecture

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-0.120+-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB.svg?style=flat-square&logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7.2-3178C6.svg?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-8.3.6-646CFF.svg?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4.17-38B2AC.svg?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat-square&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4.svg?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev/)
[![Sarvam AI](https://img.shields.io/badge/Sarvam_AI-Indic_NLP%20%26%20TTS-FF6B6B.svg?style=flat-square)](https://www.sarvam.ai/)
[![License](https://img.shields.io/badge/License-Proprietary-lightgrey.svg?style=flat-square)](#license)

**An intelligent, multi-modal career readiness and placement acceleration ecosystem for higher-education students.**

[System Architecture](#-system-architecture) •
[Key Features](#-key-features) •
[Tech Stack](#-technology-stack) •
[Installation & Setup](#-installation-and-setup) •
[API Reference](#-api-documentation) •
[Security Architecture](#-security-considerations)

</div>

---

## 📌 Project Overview

### The Problem
Traditional college placement preparation suffers from severe fragmentation:
- **Generic, Non-Personalized Advice**: Students prepare using static question banks or generalized aptitude courses detached from their actual resume, current academic background, and target roles.
- **Surface-Level Mock Interviews**: Peer-to-peer or static video practice lacks real-time adaptive questioning, audio prosody tracking, code execution, proctoring signals, or objective rubric scoring.
- **Static Resumes That Fail ATS Systems**: Students struggle to tailor multi-page academic resumes to specific job descriptions without overflowing page budgets or losing critical keywords.
- **Opaque Learning Pathways**: Online courses lack algorithmic pacing, daily study budget enforcement, spaced repetition scheduling, and sandboxed coding verification.
- **Linguistic Exclusion**: Non-native English speakers across India face steep learning curves due to a lack of accurate Indic translation and natural narration in regional tongues.

### The Solution: ARJUNA AI
**ARJUNA AI** is a production-ready, full-stack career acceleration platform. It synthesizes deterministic algorithms (TF-IDF vector matching, SM-2 spaced repetition, calendar optimization) with Google Gemini generative models and Sarvam AI Indic NLP to deliver an end-to-end preparation journey:

1. **Precision Profiling & Gap Detection**: Ingests student profiles and resumes (PDF/DOCX) to compute role-specific readiness scores and visual interactive skill maps.
2. **Adaptive Multi-Persona Interview Arena**: Conducts multi-modal interviews (technical coding via Monaco, live microphone waveforms via Wavesurfer, spoken-answer prosody metrics, and browser integrity monitoring) with comprehensive automated evaluation reports.
3. **Paced AI Learning Hub**: Generates dynamic 100-day or custom curriculum plans packed into learner daily budgets with on-demand interactive notes, YouTube conceptual breakdown, locked encrypted-grade digital notebooks, and sandboxed Python code testing.
4. **ATS-Targeted Dynamic Resume Builder**: Employs an intelligent content pool and fit-budget layout engine to output single-page, ATS-optimized resumes in both vector PDF (ReportLab) and Microsoft Word (DOCX).
5. **CareerVerse Exploration**: Offers a 20-career interactive multiverse featuring animated multi-scene career stories, Indic audio narration, salary benchmarks across experience tiers, and career comparison engines.
6. **Career Connect**: Bridges students directly to verified job platforms, internship schemes, hackathons, and certifications with AI-assisted outreach drafting.

---

## 🚀 Key Features

### 1. Student Dashboard & Analytics
- **Holistic Career Readiness Score (0–100)**: Calculated via a multi-component weighted formula:
  - Technical Skills Match ($40\%$)
  - Practical Experience & Projects ($25\%$)
  - Academic Performance ($20\%$)
  - Certifications & Achievements ($15\%$)
- **Interactive React Flow Skill-Gap Graph**: Visual node-based topology (`@xyflow/react`) mapping mastered skills, partial gaps, and missing competencies with direct links into the Learning Hub.
- **Role-Targeted Radar Analysis**: Visualizes competency coverage across selected job profiles with Recharts radar diagrams.
- **Actionable Priority Roadmap**: Automatically schedules generated tasks categorised by priority (`critical`, `high`, `medium`, `low`) with real-time status transitions.

### 2. Multi-Modal Interview Arena
- **Persona & Domain Customization**:
  - **Domains**: Software Engineering, ML/AI, Data Analytics, Management Consulting, Finance / Investment Banking, Corporate Risk, Product Management, and HR/Management.
  - **Interviewer Personas**: Technical Interviewer, HR Interviewer, Finance Expert.
  - **Seniority Tiers**: Junior ($0\text{--}3\text{ yrs}$), Mid-Level ($4\text{--}8\text{ yrs}$), Senior ($9\text{--}15\text{ yrs}$), and Leadership ($15+\text{ yrs}$).
  - **Focus Tuning**: Configurable split between Technical vs. Behavioural weighting ($0\text{--}100\%$).
- **Multi-Modal Candidate Interface**:
  - **Embedded Monaco Code Editor**: Syntax-highlighted in-browser code editor supporting multiple programming languages.
  - **Audio Prosody & Speech Metrics**: Integrates Web Speech API alongside `Wavesurfer.js` to extract volume coefficient of variation (`volume_cv`), pause detection, words-per-minute, and speaking duration.
  - **Browser Integrity Proctoring**: Monitors tab-switch occurrences, window blurs, and candidate focus anomalies.
- **Dynamic Contextual Questioning**: Reads the candidate’s active resume and parsed Job Description (PDF/DOCX) to probe genuine implementation trade-offs rather than generic trivia.
- **Post-Session Evaluation Report**:
  - Category scores and Recharts competency radar.
  - Granular feedback, identified strengths, targeted improvements, and exemplar model answers for every question.
  - Supabase Storage chunked audio/video recording with time-limited signed URL playback.
  - Optional automated email score dispatch to the student and campus placement cell via background worker tasks.

### 3. AI Learning Hub
- **Deterministic Scheduling Engine**: The `scheduler.py` module guarantees that generated study units respect student daily time budgets ($15\text{--}180\text{ mins/day}$), reserving dedicated slots for spaced revision and milestone assessments without dropping curriculum topics.
- **On-Demand Generated Materials**: Gemini generates deep notes on request with instant actions: Simplify, Go Deeper, Real-World Examples, Implementation Code, Interactive Diagram, and Follow-up Questions.
- **YouTube Conceptual Transcriptor**: Extracts closed captions via `youtube-transcript-api` (or manual transcript fallback) to construct timestamped chapters, core concepts, technical terminology glossaries, and practice flashcards.
- **Argon2-Protected Digital Notebooks**:
  - Structured chapter/page notebook shelf with animated 3D page turns.
  - Markdown-based Tiptap rich-text editor with automatic version snapshots and rollbacks.
  - Server-side lock mechanism: Notebook content is gated behind an Argon2-hashed passphrase, yielding a 30-minute scoped bearer token.
- **Multi-Format Quiz & Sandboxed Code Evaluation**:
  - Multiple Choice Questions (MCQ) with conceptual explanations.
  - Written free-form questions evaluated via Gemini against structured rubrics.
  - Coding challenges evaluated within a sandboxed Python runner (`evaluation.run_sandboxed`) executing with isolated interpreter flags (`-I`), stripped built-ins, memory scrapers, and execution timeouts.
- **Spaced Repetition System (SRS)**: Employs the SuperMemo SM-2 algorithm to dynamically schedule topic reviews based on quiz performance and recency weighting.

### 4. Dynamic ATS Resume Builder
- **Zero-Drift Live Server Preview**: The in-browser preview displays the exact vector PDF rendered on the backend by ReportLab inside an iframe, eliminating discrepancy between preview and download.
- **Candidate Pool Swapping**: Allows students to dynamically substitute project bullets, technical skills, and experience items directly from their profile repository into the resume draft.
- **Intelligent Page-Budget Layout**: Calculates content height dynamically to ensure all content stays within an optimal single-page budget.
- **Dual Format Export**:
  - **Vector PDF**: Crisp typography using bundled Inter and Roboto font families with ATS-parseable text layers.
  - **Microsoft Word (DOCX)**: Clean, styled `.docx` generated using `python-docx` for recruiter submissions.
- **Target Role Relevance Scoring**: Computes cosine similarity and keyword overlap between the resume draft and target Job Descriptions.

### 5. CareerVerse
- **Interactive Career Exploration**: 20 pre-seeded careers across engineering, data, management, and finance.
- **Multi-Scene Animated Career Stories**: SVG and CSS powered interactive narrative scenes depicting Day 1, Year 2, The Breakthrough, and Senior Leadership for every role.
- **Indic Voice Narration**: Integrated Sarvam AI text-to-speech (`bulbul:v3`) providing natural voiceover playback.
- **Comprehensive Career Insights**:
  - India salary benchmarks across entry, mid, senior, lead, and executive tiers.
  - Global comparative salary data.
  - Hiring industry leaders and common exit opportunities.
- **Side-by-Side Career Comparison**: Real-time multi-dimensional comparison of up to 3 careers simultaneously.

### 6. Career Connect
- **Curated Directories**: Pre-seeded directory spanning verified job search portals, government/corporate internship initiatives, global hackathons, and industry certifications.
- **Intelligent Recommendations**: Ranks opportunities against student profile attributes and active career preferences.
- **Status Pipeline Tracking**: Kanban-style status workflow (`Interested`, `Applied`, `Interviewing`, `Offered`, `Archived`).
- **AI Cold Outreach Generator**: Generates customized LinkedIn connection notes and recruiter outreach emails tailored to the student’s profile.

### 7. Multilingual Indic Localization
- Powered by **Sarvam AI** translation models (`mayura:v1` and `sarvam-translate:v1`).
- Native UI localization across **10 Indian Languages**: Hindi, Marathi, Gujarati, Bengali, Tamil, Telugu, Kannada, Malayalam, Punjabi, Odia, plus English.
- Context-safe translation engine: Preserves user input fields, Monaco code editors, markdown syntax, and technical code blocks unchanged.
- Two-tier caching (Client-side memory + PostgreSQL `translation_cache` table) ensures zero latency and zero repeated API costs for visited phrases.

---

## 🛠 Technology Stack

### Frontend Architecture
| Layer / Tool | Technology | Version | Purpose |
|---|---|---|---|
| **Core Framework** | React | `18.3.1` | Declarative UI component tree |
| **Language** | TypeScript | `5.7.2` | Static typing and interfaces |
| **Build & Bundler** | Vite | `8.3.6` | Fast HMR dev server and production Rollup bundling |
| **Routing** | React Router DOM | `7.18.5` | Client-side routing with protected route guards |
| **Styling** | Tailwind CSS | `3.4.17` | Utility-first responsive design and custom theme variables |
| **Animation Engine** | Motion & GSAP | `motion 14.10`, `gsap 3.15` | Fluid page transitions, scroll triggers, cinematic effects |
| **Data Visualization** | Recharts & ECharts | `recharts 2.13`, `echarts 6.1` | Readiness gauges, radar charts, salary curves |
| **Interactive Graph** | @xyflow/react | `12.12.1` | Node-edge skill-gap visual topology mapping |
| **Calendar Engine** | FullCalendar | `6.1.22` | Month and week study planner with drag-and-drop rescheduling |
| **Code Editor** | Monaco Editor | `@monaco-editor/react 4.7` | Syntax highlighting and in-browser coding interface |
| **Rich Text Editor** | Tiptap | `2.27.3` | Extensible rich-text notes editor outputting pure Markdown |
| **Audio Processing** | Wavesurfer.js | `8.0.5` | Real-time microphone audio waveform visualization |
| **Icons** | Lucide React | `0.468.0` | Clean, accessible vector iconography |

### Backend Architecture
| Layer / Tool | Technology | Version | Purpose |
|---|---|---|---|
| **API Framework** | FastAPI | `>=0.120.0` | High-performance asynchronous Python web framework |
| **ASGI Server** | Uvicorn | `>=0.38.0` | Asynchronous server implementation |
| **Database ORM** | SQLAlchemy | `>=2.0.44` | Type-annotated relational ORM and query builder |
| **Schema Validation**| Pydantic & Pydantic-Settings | `>=2.12.0` | Runtime request/response parsing and typed config validation |
| **Database Driver** | Psycopg 3 (Binary) | `>=3.2.12` | Modern PostgreSQL connection pooling and protocol driver |
| **Database Migration**| Alembic | `>=1.17.0` | Incremental database schema version control |
| **Authentication** | PyJWT & Argon2-cffi | `PyJWT 2.10`, `argon2 25.1` | Stateless HS256 JWT tokens and Argon2id password hashing |
| **Document Processing**| PyPDF & python-docx | `pypdf 6.1`, `docx 1.2` | Parsing and extracting structured text from uploaded resumes |
| **Document Engine** | ReportLab & FontTools | `reportlab 4.2`, `fonttools 4.53` | Vector single-page PDF compilation with embedded fonts |
| **HTTP Client** | HTTPX | `>=0.28.1` | Asynchronous non-blocking HTTP requests for AI providers |
| **Video Metadata** | YouTube Transcript API | `>=1.0.0` | Automatic extraction of video closed-captions |

### AI, Cloud & Media Services
| Capability | Provider / Service | Model / Specification | Functionality |
|---|---|---|---|
| **Primary LLM** | Google Gemini | `gemini-flash-lite-latest` (fallback: `gemini-3.1-flash-lite`, `gemini-flash-latest`) | Adaptive interview questions, rubric grading, learning materials |
| **Indic Translation**| Sarvam AI | `mayura:v1` / `sarvam-translate:v1` | Server-side translation into 10 Indian regional languages |
| **Indic TTS** | Sarvam AI | `bulbul:v3` (Voice: `shubh`, Pace: `1.0`) | Regional audio narration of CareerVerse career stories |
| **Object Storage** | Supabase Storage | Private bucket (`interview-recordings`) | Chunked WebM video/audio recording uploads with signed URLs |
| **Email Transport** | SMTP / Python smtplib | Standard TLS/587 | Automated interview evaluation reports dispatched to students |
| **Text Similarity** | Custom Vector Engine | `app/modules/textsim.py` | In-memory TF-IDF and Cosine similarity calculation |

---

## 🏛 System Architecture

The following diagram illustrates how the React frontend, FastAPI backend, PostgreSQL relational database, and external AI/Cloud providers interact:

```mermaid
flowchart TD
    subgraph Client["Frontend Client (React 18 + Vite)"]
        UI["User Interface (Tailwind CSS + Motion)"]
        Router["React Router (Auth & Protected Guards)"]
        State["Client State & Auth Provider"]
        Monaco["Monaco Editor"]
        Wave["Wavesurfer.js Audio"]
        Canvas["React Flow & Recharts"]
    end

    subgraph Gateway["API Gateway & Middleware"]
        CORS["CORS Policy Validation"]
        Timing["Request Timing Middleware"]
        AuthMid["JWT Bearer Authentication Handler"]
    end

    subgraph Backend["Backend Application (FastAPI)"]
        RouterHub["API Router Hub (/api)"]
        
        subgraph SubModules["Application Modules"]
            ModAuth["Auth & User Service"]
            ModProfile["Profile & Resume Parser"]
            ModDash["Scoring & Readiness Engine"]
            ModArena["Interview Arena Controller"]
            ModLearn["Learning Hub & Scheduler"]
            ModResume["ATS Resume Builder"]
            ModCareer["CareerVerse & Insights"]
            ModConnect["Career Connect Directory"]
            ModTrans["Translation & Narration Engine"]
            ModSandbox["Sandboxed Code Evaluation"]
        end
    end

    subgraph Storage["Persistence Layer"]
        DB[(PostgreSQL Database)]
        Alembic["Alembic Migrations"]
        Cache[("Translation Cache Table")]
    end

    subgraph CloudServices["External AI & Cloud Infrastructure"]
        Gemini["Google Gemini API (Flash Lite / 2.5)"]
        SarvamTrans["Sarvam Translation API"]
        SarvamTTS["Sarvam Text-To-Speech (Bulbul)"]
        SupaStore["Supabase S3 Storage (Recordings)"]
        SMTP["SMTP Mail Server"]
    end

    %% Client Interactions
    UI --> Router
    Router --> State
    State --> Gateway
    Monaco --> State
    Wave --> State
    Canvas --> State

    %% Gateway to Backend
    Gateway --> CORS
    CORS --> Timing
    Timing --> AuthMid
    AuthMid --> RouterHub

    %% Routing to Modules
    RouterHub --> ModAuth
    RouterHub --> ModProfile
    RouterHub --> ModDash
    RouterHub --> ModArena
    RouterHub --> ModLearn
    RouterHub --> ModResume
    RouterHub --> ModCareer
    RouterHub --> ModConnect
    RouterHub --> ModTrans

    %% Backend to Database
    ModAuth <--> DB
    ModProfile <--> DB
    ModDash <--> DB
    ModArena <--> DB
    ModLearn <--> DB
    ModResume <--> DB
    ModCareer <--> DB
    ModConnect <--> DB
    ModTrans <--> Cache
    Cache <--> DB
    Alembic -.-> DB

    %% Backend to External Services
    ModArena <--> Gemini
    ModArena --> SupaStore
    ModArena --> SMTP
    ModLearn <--> Gemini
    ModLearn --> ModSandbox
    ModTrans <--> SarvamTrans
    ModTrans <--> SarvamTTS
```

---

## 📂 Project Structure

```
ARJUNA-AI/
├── .gitignore
├── README.md                          # Comprehensive project documentation
├── TEAM_SETUP.md                      # Team database and environment coordination guide
├── arjuna_ai_backup.dump              # PostgreSQL reference database dump
│
├── docs/                              # Technical guides and documentation
│   ├── AI_LEARNING_HUB.md             # Deep dive into Learning Hub scheduling and sandboxing
│   ├── DEPLOYMENT.md                  # Vercel and Supabase production deployment guide
│   ├── FRONTEND.md                    # Detailed frontend component and library reference
│   ├── Hackathons_and_Competitions.txt# Directory source for competitions
│   └── Job_Platforms_and_Internship_Opportunities.txt # Directory source for job platforms
│
├── backend/                           # FastAPI Application Root
│   ├── alembic.ini                    # Alembic migration configuration
│   ├── requirements.txt               # Backend Python dependencies
│   ├── vercel.json                    # Vercel serverless deployment config
│   ├── .env.example                   # Environment variable template
│   │
│   ├── alembic/                       # Database schema migration revisions
│   │   ├── env.py                     # Migration runtime environment
│   │   └── versions/                  # Revision files (initial, learning, interview, etc.)
│   │
│   ├── api/                           # Serverless entrypoint
│   │   └── [...path].py               # Catch-all handler for Vercel deployment
│   │
│   ├── app/                           # Core Application Code
│   │   ├── main.py                    # FastAPI application initialization & lifespan
│   │   ├── api/                       # API router definitions
│   │   │   ├── router.py              # Central APIRouter aggregating all sub-routers
│   │   │   └── routes/                # Endpoint route files (auth, learning, interview...)
│   │   ├── core/                      # Application core configuration
│   │   │   ├── config.py              # Pydantic BaseSettings environment parsing
│   │   │   ├── security.py            # Argon2 password hashing and JWT token handlers
│   │   │   └── logging_config.py      # Structured JSON/console logging setup
│   │   ├── db/                        # Database connectivity
│   │   │   ├── base.py                # DeclarativeBase SQLAlchemy mapper
│   │   │   └── session.py             # Engine initialization and sessionmaker
│   │   ├── models/                    # SQLAlchemy database entity models
│   │   │   ├── user.py                # User and StudentSettings entities
│   │   │   ├── profile.py             # StudentProfile, AcademicDetail, Skills, Projects
│   │   │   ├── interview.py           # InterviewSession entity
│   │   │   ├── learning.py            # LearningPlan, Task, Notebook, Quiz, Mastery entities
│   │   │   ├── careerverse.py         # Career, Salary, Scene, Fit, Trajectory entities
│   │   │   ├── resume_builder.py      # ResumeVersion entity
│   │   │   ├── career_connect.py      # CareerConnectSavedItem entity
│   │   │   └── translation.py         # TranslationCache entity
│   │   ├── modules/                   # Isolated business logic engines
│   │   │   ├── auth/                  # Authentication service and route dependencies
│   │   │   ├── scoring/               # Career readiness computation engine & roadmaps
│   │   │   ├── learning/              # Planner, scheduler, SRS mastery, sandbox evaluator
│   │   │   ├── resume_builder/        # ATS layout optimizer, PDF & DOCX renderers
│   │   │   ├── interview_speech.py    # Voice prosody analysis
│   │   │   ├── interview_recording.py # Chunked upload to Supabase Storage
│   │   │   ├── interview_email.py     # Background score email dispatch
│   │   │   ├── textsim.py             # In-memory TF-IDF & Cosine similarity (Vercel-safe)
│   │   │   └── translate.py           # Sarvam AI translation client and cache manager
│   │   ├── schemas/                   # Pydantic request and response schemas
│   │   ├── data/                      # Reference seed datasets (careers, India salaries)
│   │   └── seeds/                     # Database seed execution scripts
│   │
│   ├── scripts/                       # Maintenance and database sync scripts
│   └── tests/                         # Pytest test suite (learning logic, scoring, API)
│
└── frontend/                          # React Application Root
    ├── package.json                   # NPM dependencies and scripts
    ├── vite.config.ts                 # Vite bundler configuration & dev server proxy
    ├── tailwind.config.js             # Tailwind typography and theme design tokens
    ├── tsconfig.json                  # TypeScript compiler settings
    ├── vercel.json                    # Single-page app rewrite configuration
    ├── .env.example                   # Frontend environment variable template
    │
    ├── public/                        # Static assets (assistant avatar, careerverse scenes)
    └── src/
        ├── App.tsx                    # Route definitions and authentication wrappers
        ├── main.tsx                   # React root hydration
        ├── components/                # Reusable UI components
        │   ├── ui.tsx                 # Core atomic controls (Button, Card, Input, Modal)
        │   ├── layout.tsx             # Authenticated application shell, sidebar & navbar
        │   ├── CodeEditor.tsx         # Monaco editor wrapper
        │   ├── Waveform.tsx           # Wavesurfer.js live microphone component
        │   ├── SkillMap.tsx           # Interactive React Flow skill gap map
        │   ├── Assistant.tsx          # Floating guide assistant widget
        │   └── learning/              # Calendar, RichEditor, Notebook, Quiz components
        ├── pages/                     # Routed page views
        │   ├── Landing.tsx            # Cinematic hero landing page
        │   ├── Auth.tsx               # Sign-in and registration views
        │   ├── Onboarding.tsx         # Multi-step profile wizard & resume extraction
        │   ├── Dashboard.tsx          # Readiness score and priority roadmap
        │   ├── InterviewArena.tsx     # Adaptive mock interview interface & report
        │   ├── ResumeBuilder.tsx      # ATS resume editor with real-time PDF preview
        │   ├── CareerVerse.tsx        # Career exploration grid
        │   ├── CareerStory.tsx        # Multi-scene animated career narrative
        │   ├── CareerInsights.tsx     # Salary, hiring company, and skill insights
        │   ├── CareerCompare.tsx      # Multi-career comparison view
        │   ├── CareerConnect.tsx      # Opportunities directory and outreach generator
        │   ├── Settings.tsx           # Account preferences and password update
        │   └── learning/              # Learning Hub tab views (Overview, Planner, Notes...)
        ├── lib/                       # Client utilities
        │   ├── api.ts                 # HTTP client with automatic Authorization headers
        │   ├── auth.tsx               # AuthContext session provider
        │   ├── i18n.tsx               # Sarvam AI Indic translation context provider
        │   └── resume.ts              # Resume builder state management helpers
        └── styles/
            └── index.css              # Custom scrollbars, animations, and Tailwind directives
```

---

## ⚙️ Installation and Setup

### Prerequisites
- **Python**: Version `3.11` or `3.12`
- **Node.js**: Version `18.x` or `20.x` (with `npm` package manager)
- **PostgreSQL**: Version `15+` (Local installation or hosted instance on Supabase)
- **Git**

---

### Step 1: Clone Repository
```bash
git clone https://github.com/your-username/ARJUNA-AI.git
cd ARJUNA-AI
```

---

### Step 2: Backend Setup

1. **Create and Activate Python Virtual Environment**:
   - **Windows (PowerShell)**:
     ```powershell
     cd backend
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     cd backend
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. **Install Python Dependencies**:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Open `backend/.env` and configure your credentials (see [Environment Variables](#-environment-variables)). At minimum, set `DATABASE_URL`, `JWT_SECRET`, and `GEMINI_API_KEY`.

4. **Run Database Migrations**:
   Ensure your PostgreSQL service is running and the target database exists:
   ```bash
   python -m alembic upgrade head
   ```

5. **Seed Reference Datasets**:
   Populate core roles, career tracks, topics, and CareerVerse catalogs:
   ```bash
   # Seed core catalog (domains, roles, required skills)
   python -m app.seeds.seed

   # Seed AI Learning Hub tracks and topics (20 tracks, 249 topics)
   python -m app.seeds.learning_seed

   # Seed CareerVerse profiles, salary data, and animated stories
   python -m app.seeds.careerverse_seed
   ```

6. **Start Backend Server**:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   Verify backend health at `http://127.0.0.1:8000/health` or browse the interactive OpenAPI documentation at `http://127.0.0.1:8000/docs`.

---

### Step 3: Frontend Setup

1. **Navigate and Install Node Modules**:
   Open a new terminal window:
   ```bash
   cd frontend
   npm install --legacy-peer-deps
   ```
   > *Note*: `--legacy-peer-deps` is required due to React 18 plugin peer-dependency matching on Vite 8.

2. **Configure Frontend Environment**:
   ```bash
   cp .env.example .env
   ```
   Ensure `.env` contains:
   ```env
   VITE_API_BASE=/api
   ```
   *(During local development, Vite proxies requests from `/api` to `http://127.0.0.1:8000/api` automatically).*

3. **Start Frontend Development Server**:
   ```bash
   npm run dev
   ```
   Open your browser at `http://localhost:5173`.

---

## 🔐 Environment Variables

### Backend Configuration (`backend/.env`)

| Variable Name | Required | Default Value | Description |
|---|:---:|---|---|
| `DATABASE_URL` | **Yes** | `postgresql+psycopg://postgres:postgres@localhost:5432/arjuna_ai` | PostgreSQL connection URI using the Psycopg 3 driver (`postgresql+psycopg://...`). |
| `DB_ECHO` | No | `false` | When `true`, SQLAlchemy logs all executed SQL statements to the console. |
| `JWT_SECRET` | **Yes** | `replace-with-a-long-random-string` | Cryptographic secret for signing HS256 authentication tokens. (Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`). |
| `JWT_ALGORITHM` | No | `HS256` | JWT signature algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Lifespan of issued access tokens before expiration. |
| `CORS_ORIGINS` | **Yes** | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of permitted origin URLs for CORS security. |
| `FRONTEND_URL` | No | `http://localhost:5173` | Canonical public URL of the frontend application. |
| `UPLOAD_DIR` | No | `./uploads` | Local directory for holding temporary uploaded resumes and font caches. (Automatically sets to `/tmp/uploads` on Vercel). |
| `MAX_UPLOAD_SIZE_MB` | No | `5` | Maximum allowed payload size for uploaded resume documents. |
| `ENVIRONMENT` | No | `development` | Deployment environment identifier (`development` or `production`). |
| `DEBUG` | No | `true` | Enables verbose debug outputs and exception traces. |
| `LOG_LEVEL` | No | `INFO` | Console logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `GEMINI_API_KEY` | **Yes\*** | *None* | Google AI Studio key. (\*Required for Interview Arena, Quiz generation, and AI Learning materials). |
| `GEMINI_MODEL` | No | `gemini-flash-lite-latest` | Primary Gemini model utilized for real-time generative responses. |
| `GEMINI_FALLBACK_MODELS` | No | `gemini-3.1-flash-lite,gemini-flash-latest,gemini-2.5-flash-lite` | Ordered fallback models invoked automatically on quota exhaustion (HTTP 429/503). |
| `SARVAM_API_KEY` | No | *None* | Sarvam AI API key for regional Indic language translation and TTS narration. |
| `SARVAM_TRANSLATE_MODEL`| No | `mayura:v1` | Model identifier for translation requests (`mayura:v1` or `sarvam-translate:v1`). |
| `SARVAM_TTS_MODEL` | No | `bulbul:v3` | Model identifier for Sarvam Text-to-Speech audio generation. |
| `SARVAM_TTS_SPEAKER` | No | `shubh` | Voice identifier for Sarvam TTS narration (`shubh`, `aditya`, `ritu`, `priya`). |
| `SARVAM_TTS_PACE` | No | `1.0` | Playback speed multiplier for generated narration audio. |
| `EMAIL_ALERTS_ENABLED` | No | `false` | Enables asynchronous dispatch of interview evaluation emails. |
| `SMTP_HOST` | No | *None* | Hostname of the outbound SMTP server (e.g., `smtp.gmail.com`). |
| `SMTP_PORT` | No | `587` | Outbound SMTP connection port (TLS). |
| `SMTP_USERNAME` | No | *None* | Username / email address for authenticating with the SMTP server. |
| `SMTP_PASSWORD` | No | *None* | App password or token for SMTP authentication. |
| `SMTP_FROM` | No | *None* | Sender header address for outbound emails. |
| `ALERT_EMAIL_TO` | No | *None* | Optional administrator/faculty email address copied on all student reports. |
| `SUPABASE_URL` | No | *None* | Supabase project API URL (Required for interview video recording storage). |
| `SUPABASE_SERVICE_ROLE_KEY` | No | *None* | Supabase backend service-role key (Must never be exposed to the frontend). |
| `SUPABASE_RECORDINGS_BUCKET`| No | `interview-recordings` | Private Supabase Storage bucket for persisting interview recording chunks. |

### Frontend Configuration (`frontend/.env`)

| Variable Name | Required | Default Value | Description |
|---|:---:|---|---|
| `VITE_API_BASE` | **Yes** | `/api` | Base path for all backend API calls. Points to `/api` locally (proxied by Vite) or full URL in production (`https://api.yourdomain.com/api`). |

---

## 🗄 Database Design

The PostgreSQL database schema is managed via **SQLAlchemy 2.0** and versioned through **Alembic**. It contains 40+ relational tables structured into distinct logical domains:

```mermaid
erDiagram
    USERS ||--|| STUDENT_PROFILES : "has one"
    USERS ||--o{ ACADEMIC_DETAILS : "records"
    USERS ||--o{ STUDENT_SKILLS : "possesses"
    USERS ||--o{ EXPERIENCES : "accumulates"
    USERS ||--o{ PROJECTS : "builds"
    USERS ||--o{ RESUMES : "uploads"
    USERS ||--o{ ROLE_ASSESSMENTS : "evaluated for"
    USERS ||--o{ INTERVIEW_SESSIONS : "attempts"
    USERS ||--o{ LEARNING_PLANS : "enrolls"
    USERS ||--o{ NOTEBOOKS : "authors"
    USERS ||--o{ QUIZ_SESSIONS : "submits"
    USERS ||--o{ RESUME_VERSIONS : "crafts"

    JOB_ROLES ||--o{ ROLE_REQUIRED_SKILLS : "specifies"
    SKILLS ||--o{ ROLE_REQUIRED_SKILLS : "mapped to"
    JOB_ROLES ||--o{ ROLE_ASSESSMENTS : "evaluated against"
    
    ROLE_ASSESSMENTS ||--o{ SKILL_GAP_ANALYSES : "produces"
    ROLE_ASSESSMENTS ||--|| IMPROVEMENT_ROADMAPS : "generates"
    IMPROVEMENT_ROADMAPS ||--o{ ROADMAP_TASKS : "contains"

    LEARNING_TRACKS ||--o{ LEARNING_TOPICS : "contains"
    LEARNING_PLANS ||--o{ LEARNING_TASKS : "schedules"
    LEARNING_TOPICS ||--o{ TOPIC_PROFICIENCIES : "tracks"
    
    NOTEBOOKS ||--o{ NOTEBOOK_CHAPTERS : "divides into"
    NOTEBOOK_CHAPTERS ||--o{ NOTEBOOK_PAGES : "holds"
    NOTEBOOK_PAGES ||--o{ NOTEBOOK_PAGE_VERSIONS : "snapshots"

    CAREERS ||--o{ CAREER_SALARIES : "benchmarks"
    CAREERS ||--o{ CAREER_SKILLS : "demands"
    CAREERS ||--o{ CAREER_STORIES : "narrates"
    CAREER_STORIES ||--o{ CAREER_STORY_SCENES : "renders"
```

### Major Entity Overview

1. **Authentication & Student Identity**:
   - `users`: Core identity table (id, email, username, hashed_password via Argon2id, full_name, onboarding_completed, created_at).
   - `student_profiles`: Academic baseline (college, degree, branch, cgpa, graduation_year, bio, completion_percentage).
   - `academic_details`: Multi-level educational history (10th, 12th, undergraduate, coursework).
   - `student_skills`: Extracted and claimed skills with verified evidence counts and proficiency levels (`beginner`, `intermediate`, `advanced`).
   - `projects` & `project_technologies`: Detailed software/engineering projects with role contributions and tech stacks.
   - `experiences`: Internships and full-time employment roles.
   - `resumes`: Metadata and extracted full-text of uploaded documents.

2. **Readiness & Evaluation Engine**:
   - `career_domains` & `job_roles`: Supported professional domains and career tracks.
   - `skills` & `role_required_skills`: Industry skill requirements with importance classifications (`must_have`, `good_to_have`, `optional`).
   - `role_assessments`: Calculated student scores per target role (overall_score, technical_score, experience_score, academic_score, certification_score, readiness_band).
   - `skill_gap_analyses`: Granular skill deficit matrix per role assessment (`missing`, `partial`, `met`).
   - `improvement_roadmaps` & `roadmap_tasks`: Generated actionable task pipelines with assigned priority and status.

3. **Interview Arena**:
   - `interview_sessions`: Complete interview lifecycle (domain, seniority, personas, transcript JSONB array, integrity_signals JSONB array, report metrics JSONB, Supabase recording pointers).

4. **AI Learning Hub**:
   - `learning_tracks` & `learning_topics`: 20 tracks, 249 granular topics, and prerequisite dependency graphs.
   - `learning_plans` & `learning_tasks`: Personalized study curricula packed into calendar slots.
   - `generated_materials`: Deep-dive AI study notes cached per topic and phase.
   - `notebooks`, `notebook_chapters`, `notebook_pages`, `notebook_page_versions`: Digital markdown note repository with password protection and historical snapshots.
   - `quiz_sessions`, `quiz_questions`, `quiz_attempts`: Evaluated tests containing MCQ, rubric-graded open responses, and sandboxed code submissions.
   - `topic_proficiencies` & `revision_schedules`: SuperMemo SM-2 spaced repetition state (ease factor, interval, review dates).

5. **Dynamic Resume Builder**:
   - `resume_versions`: Structured JSON state of tailored resumes (selected contact details, reordered projects, prioritized skills, custom styling tokens, target job description fit).

6. **CareerVerse & Career Connect**:
   - `careers`, `career_salaries`, `career_skills`, `career_companies`, `career_exits`: Comprehensive market data across 20 professions.
   - `career_stories` & `career_story_scenes`: Scene data, SVG graphical layouts, and narration voiceover scripts.
   - `user_career_fit` & `user_career_progress`: Computed suitability percentages and read progression.
   - `career_connect_saved_items`: Student-curated job boards, hackathons, and certifications with application status pipelines.
   - `translation_cache`: Shared server-side string translation store indexed by source hash and target language.

---

## 📡 API Documentation

The backend exposes a RESTful API with all routes nested beneath the `/api` prefix. Interactive Swagger/OpenAPI documentation is available at `/docs`.

### 1. Authentication & Identity (`/api/auth`)
| Method | Endpoint | Access | Purpose |
|---|---|:---:|---|
| `POST` | `/auth/register` | Public | Registers a new student account, initializes profile, issues JWT bearer token. |
| `POST` | `/auth/login` | Public | Authenticates credentials (email/username + password), returns JWT bearer token. |
| `GET` | `/auth/me` | Authenticated | Retrieves current authenticated user profile and onboarding progress. |
| `GET` | `/auth/availability` | Public | Real-time validation checking if email or username is already registered. |
| `POST` | `/auth/change-password` | Authenticated | Validates existing password and applies Argon2id hashed replacement. |
| `POST` | `/auth/logout` | Authenticated | Logs logout activity and instructs client to discard the bearer token. |

### 2. Onboarding & Profile Management (`/api/onboarding`, `/api/profile`, `/api/resume`)
| Method | Endpoint | Access | Purpose |
|---|---|:---:|---|
| `GET` | `/onboarding/status` | Authenticated | Returns current step completion status of the onboarding wizard. |
| `POST` | `/onboarding/{step}` | Authenticated | Updates personal, academic, skill, project, or career preference steps. |
| `POST` | `/resume/upload` | Authenticated | Parses uploaded PDF/DOCX resume and extracts skills, projects, and work history. |
| `POST` | `/resume/import` | Authenticated | Ingests confirmed parsed resume entities directly into student profile tables. |
| `PUT` | `/profile/{section}` | Authenticated | Updates existing profile records (academics, skills, projects, experience). |

### 3. Dashboard & Readiness (`/api/dashboard`)
| Method | Endpoint | Access | Purpose |
|---|---|:---:|---|
| `GET` | `/dashboard` | Authenticated | Delivers overall readiness score, category breakdowns, radar metrics, and tasks. |
| `GET` | `/dashboard/roles/{slug}`| Authenticated | Retrieves deep gap analysis and skill deficit matrix for a specific target role. |
| `POST` | `/dashboard/recalculate` | Authenticated | Forces complete re-evaluation of readiness algorithms against updated profile. |
| `GET` | `/roadmap` | Authenticated | Lists prioritized improvement tasks scheduled for the student. |
| `PATCH`| `/roadmap/tasks/{id}` | Authenticated | Toggles task execution status (`pending`, `in_progress`, `completed`). |

### 4. Interview Arena (`/api/interviews`)
| Method | Endpoint | Access | Purpose |
|---|---|:---:|---|
| `GET` | `/interviews` | Authenticated | Retrieves historical list of past mock interview sessions and reports. |
| `POST` | `/interviews` | Authenticated | Initializes a new interview session and generates opening question via Gemini. |
| `POST` | `/interviews/job-description` | Authenticated | In-memory text extraction from uploaded Job Description PDF/DOCX. |
| `GET` | `/interviews/{id}` | Authenticated | Retrieves transcript, telemetry, and report status for a specific session. |
| `POST` | `/interviews/{id}/answer` | Authenticated | Saves student answer + voice metrics, triggers Gemini evaluation & next question. |
| `POST` | `/interviews/{id}/end` | Authenticated | Concludes session, computes final report, triggers async email dispatch. |
| `POST` | `/interviews/{id}/recording/chunk` | Authenticated | Appends streaming WebM audio/video chunk to Supabase Storage. |
| `POST` | `/interviews/{id}/recording/finalize` | Authenticated | Completes multi-part recording upload and marks storage key. |
| `GET` | `/interviews/{id}/recording/url` | Authenticated | Generates a 60-minute expiring signed URL for recording playback. |

### 5. AI Learning Hub (`/api/learning`)
| Method | Endpoint | Access | Purpose |
|---|---|:---:|---|
| `GET` | `/learning/overview` | Authenticated | Learner dashboard: active plan summary, streak counter, upcoming milestones. |
| `GET` | `/learning/tracks` | Authenticated | Catalog of 20 career learning tracks with topic counts and descriptions. |
| `POST` | `/learning/plans` | Authenticated | Creates a new curriculum plan packed into daily calendar budgets via `scheduler.py`. |
| `GET` | `/learning/plans/{id}/calendar` | Authenticated | Retrieves FullCalendar formatted events for month/week schedule views. |
| `PATCH`| `/learning/tasks/{id}` | Authenticated | Updates task status or reschedules date via drag-and-drop. |
| `POST` | `/learning/materials` | Authenticated | Generates on-demand markdown study guide for a specified topic. |
| `POST` | `/learning/materials/{id}/action` | Authenticated | Triggers AI modifications: `simplify`, `deepen`, `examples`, `code`, `diagram`. |
| `POST` | `/learning/youtube` | Authenticated | Extracts captions from YouTube URL and generates conceptual breakdowns. |
| `POST` | `/learning/notebooks` | Authenticated | Creates a new digital notebook with optional Argon2 lock password. |
| `POST` | `/learning/notebooks/{id}/unlock`| Authenticated | Validates password and grants 30-minute scoped notebook bearer token. |
| `POST` | `/learning/quizzes` | Authenticated | Generates adaptive MCQ, rubric written, or sandboxed coding assessment. |
| `POST` | `/learning/quizzes/{id}/submit` | Authenticated | Submits answers; executes coding tests in sandbox; grades written via rubrics. |
| `GET` | `/learning/revisions` | Authenticated | Lists topics currently due for review under the SM-2 Spaced Repetition System. |

### 6. Dynamic Resume Builder (`/api/resume-builder`)
| Method | Endpoint | Access | Purpose |
|---|---|:---:|---|
| `GET` | `/resume-builder/versions` | Authenticated | Lists all saved resume versions for the student. |
| `POST` | `/resume-builder/generate` | Authenticated | Initializes a resume draft tailored to a target role from student profile data. |
| `GET` | `/resume-builder/versions/{id}` | Authenticated | Retrieves full structured JSON state of a specific resume version. |
| `PUT` | `/resume-builder/versions/{id}` | Authenticated | Saves modified resume fields, reordered entries, and styling preferences. |
| `POST` | `/resume-builder/versions/{id}/swap` | Authenticated | Swaps an active project or bullet with an alternate item from profile pool. |
| `GET` | `/resume-builder/versions/{id}/pdf` | Authenticated | Streams compiled vector PDF generated on the fly via ReportLab. |
| `GET` | `/resume-builder/versions/{id}/docx` | Authenticated | Streams clean formatted Microsoft Word `.docx` file via python-docx. |

### 7. CareerVerse & Career Connect (`/api/careers`, `/api/career-connect`)
| Method | Endpoint | Access | Purpose |
|---|---|:---:|---|
| `GET` | `/careers` | Authenticated | Catalogs 20 professions with category filters and median pay. |
| `GET` | `/careers/{slug}` | Authenticated | In-depth career specification: skills, companies, salaries, and exit options. |
| `GET` | `/career-stories/{slug}` | Authenticated | Retrieves 4-scene narrative scripts and visual storyboard data. |
| `GET` | `/career-fit` | Authenticated | Ranks all 20 careers by calculated suitability percentage for current student. |
| `POST` | `/career-comparison` | Authenticated | Multi-attribute comparison payload for up to 3 selected careers. |
| `GET` | `/career-connect/directory` | Authenticated | Directory of curated jobs, internships, hackathons, and certifications. |
| `POST` | `/career-connect/saved` | Authenticated | Saves opportunity to student's personal pipeline. |
| `POST` | `/career-connect/message-draft` | Authenticated | AI cold-outreach message generator tailored to opportunity and candidate. |

### 8. Localization & Narration (`/api/translate`, `/api/narration`)
| Method | Endpoint | Access | Purpose |
|---|---|:---:|---|
| `POST` | `/translate` | Authenticated | Translates text payloads into requested Indian languages via Sarvam AI. |
| `GET` | `/translate/languages` | Public | Lists supported Indic language codes and localized display names. |
| `POST` | `/narration/speak` | Authenticated | Synthesizes speech audio from text using Sarvam Bulbul TTS. |

---

## 🤖 AI Integrations

ARJUNA AI enforces a strict architectural boundary: **Generative models write content and evaluations; deterministic Python code manages structures, schedules, constraints, and scoring.**

```mermaid
flowchart LR
    subgraph Generative["Generative AI Layer (Google Gemini)"]
        G1["Interview Questioning"]
        G2["Rubric Answer Grading"]
        G3["Concept Notes & YouTube Summaries"]
        G4["Cold Outreach Messages"]
    end

    subgraph Deterministic["Deterministic Code Layer (Python / FastAPI)"]
        D1["Schedule Packing & Duration Caps (scheduler.py)"]
        D2["Code Sandbox Execution (audit hooks + -I)"]
        D3["Readiness Scoring & TF-IDF (textsim.py)"]
        D4["SM-2 Spaced Repetition (srs.py)"]
        D5["ATS Page-Budget Layout (ReportLab)"]
    end

    subgraph Indic["Indic Language Layer (Sarvam AI)"]
        S1["Mayura Translation Engine"]
        S2["Bulbul TTS Voice Narration"]
        S3["PostgreSQL String Cache"]
    end

    Generative <--> Deterministic
    Deterministic <--> Indic
```

### 1. Adaptive Interview Arena (Google Gemini)
- **Role**: Emulates a human interviewer across selected personas (Technical, HR, Finance) and seniority levels.
- **Prompt Injection Defense**: When candidates upload arbitrary Job Descriptions, the backend wraps the text in isolated reference blocks, explicitly directing Gemini to disregard candidate-authored instructions inside the document.
- **Fail-Soft Persistence**: Candidate responses are committed to PostgreSQL *prior* to issuing the external API call to Gemini. If the provider returns HTTP 429 (quota) or times out, the answer is safe, and the session can still be evaluated cleanly.
- **Multi-Model Fallback Cascade**: If the primary model (`gemini-flash-lite-latest`) experiences transient outages or quota exhaustion, requests automatically roll through `GEMINI_FALLBACK_MODELS` (`gemini-3.1-flash-lite`, `gemini-flash-latest`, `gemini-2.5-flash-lite`).

### 2. Code Execution Sandbox (`app/modules/learning/evaluation.py`)
To prevent arbitrary code execution vulnerabilities during coding quizzes, ARJUNA AI runs Python solutions inside a fortified local sandbox:
- Invokes a clean sub-process interpreter with isolated mode (`python -I`).
- Strips host environment variables and executes inside an ephemeral scratch directory.
- Enforces an import allow-list (restricting access to `math`, `collections`, `itertools`, `heapq`, `json`, etc.).
- Registers Python runtime audit hooks (`sys.addaudithook`) that intercept and abort all attempts to open network sockets, access raw files outside scratch, or spawn child processes.
- Enforces a hard execution timeout ($5.0\text{ seconds}$).

### 3. Spaced Repetition Engine (`app/modules/learning/srs.py`)
Learning revision schedules implement the **SuperMemo SM-2** algorithm:
$$\text{EF}' = \text{EF} + (0.1 - (5 - q) \times (0.08 + (5 - q) \times 0.02))$$
Where $q \in [0, 5]$ represents the student's quiz score quality, and $\text{EF}$ is the topic Ease Factor (bounded at a minimum of $1.3$). Topics scoring below threshold are reset to 1-day review intervals, ensuring scientific retention without manual planning.

### 4. ATS Content Layout & Word Fit Engine
Rather than relying on non-deterministic client-side HTML canvas rendering, the Resume Builder evaluates layout bounding boxes directly inside ReportLab:
- Reads font metrics from bundled TrueType fonts (`Inter` and `Roboto`).
- Calculates dynamic line wrapping and vertical point consumption for each section.
- Prevents page-overflow by presenting an on-screen "Page Budget Meter" that advises students when content must be trimmed before compiling the vector PDF.

---

## 📖 Usage Guide: The Student Journey

```mermaid
sequenceDiagram
    autonumber
    actor Student as Student Candidate
    participant Auth as Auth & Onboarding
    participant Dash as Dashboard
    participant Arena as Interview Arena
    participant Hub as Learning Hub
    participant Builder as Resume Builder

    Student->>Auth: Register Account & Upload Existing Resume
    Auth->>Auth: Extract Skills, Academics, Projects via PyPDF
    Auth->>Dash: Calculate Baseline Readiness Score
    Dash-->>Student: Display Readiness Score (0-100) & Skill Map

    Student->>Arena: Start Mock Interview (Set Domain & Seniority)
    Arena->>Student: Ask Opening Question & Display Waveform
    Student->>Arena: Dictate Spoken Answer & Code Solution
    Arena-->>Student: Deliver Real-Time Feedback & Radar Report

    Student->>Hub: Enroll in Target Learning Track
    Hub->>Hub: Generate Paced Calendar Plan (Scheduler)
    Student->>Hub: Read Generated Notes & Complete Coding Quizzes
    Hub->>Dash: Update Topic Mastery & Recalculate Readiness

    Student->>Builder: Initialize Tailored Resume Version
    Builder->>Builder: Match Target JD Keywords & Enforce 1-Page Budget
    Builder-->>Student: Download Vector ATS PDF & Word DOCX
```

1. **Sign Up & Automated Onboarding**:
   - Register at `/register`. Enter full name, username, email, and password.
   - Upload your existing resume (PDF or DOCX). The backend parser automatically extracts your educational history, tech stack, project descriptions, and internships.
   - Confirm or refine extracted records across the multi-step onboarding wizard.

2. **Explore Readiness on the Dashboard**:
   - Inspect your overall readiness score and explore the interactive skill map.
   - Click on missing or partial skill nodes to view remediation steps and recommended curriculum tracks.
   - Review prioritized tasks in your personalized improvement roadmap.

3. **Practice in the Interview Arena**:
   - Navigate to `/app/interview-arena`. Select your domain (e.g., *Software Engineering*), target seniority (e.g., *Junior*), and balance your Technical vs. Behavioural focus.
   - Optionally paste or upload the specific Job Description for the job you are targeting.
   - Grant browser microphone and camera permissions. Answer questions verbally (monitoring live waveforms) or write implementation solutions inside the Monaco editor.
   - Click **End Interview** to generate a comprehensive evaluation report. Review radar scores, model answers, and have a copy emailed directly to your inbox.

4. **Master Deficits in the AI Learning Hub**:
   - Choose a track (e.g., *Full Stack Web Development* or *Machine Learning Engineer*).
   - Generate a structured study plan based on your preferred daily time budget (e.g., 45 mins/day).
   - Use the calendar view to track daily units. Drag-and-drop tasks to balance missed days.
   - Generate on-demand study guides, import YouTube tutorials for automated concept extractions, and record notes in your encrypted digital notebook.
   - Complete MCQs and coding challenges to advance your topic mastery levels.

5. **Craft an ATS-Optimized Resume**:
   - Navigate to `/app/resume-builder`. Create a resume version tailored to a specific company or role.
   - Reorder projects and experience bullets using drag-and-drop.
   - Swap bullets from your profile pool to maximize keyword relevance against target job descriptions while monitoring the single-page budget meter.
   - Download the final document as a vector-rendered PDF or an editable Microsoft Word document.

6. **Navigate Careers & Opportunities**:
   - Browse the **CareerVerse** catalog to read animated day-in-the-life career stories, listen to regional voice narration, and review entry-to-executive salary trajectories.
   - Use **Career Connect** to discover verified internships, hackathons, and certifications, and generate customized outreach messages to connect with recruiters.

---

## 🔒 Security Considerations

ARJUNA AI implements defense-in-depth principles across authentication, database access, media storage, and execution layers:

### 1. Password Hashing & Secret Derivation
- Passwords are never stored in plaintext. Hashing is performed using **Argon2id** (`argon2-cffi`), the memory-hard password hashing winner of the Password Hashing Competition.
- Notebook locking utilizes independent Argon2id salt derivation to ensure compromised user account passwords do not automatically compromise locked private notebooks.

### 2. Stateless JWT Authentication
- Session tokens are signed using **HMAC-SHA256 (HS256)** with an explicit expiration window (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- The JWT payload encapsulates only identity metadata (`sub: user_id`). No credentials, passwords, or personal identifying tokens are placed in claims.
- Fast, typed FastAPI dependency injection (`CurrentUser`, `DbSession`) validates the token on every protected route and guarantees that query filters scope strictly to the authenticated `user_id`.

### 3. Safe File Ingestion & Parsing
- All document uploads (`/resume/upload`, `/interviews/job-description`) validate file sizes against an enforced ceiling ($5\text{ MB}$).
- **Magic-Byte Sniffing**: Validates binary header signatures (`%PDF` for PDF, `PK\x03\x04` for DOCX) to prevent malicious executable files disguised with arbitrary file extensions.
- In serverless runtime environments (such as Vercel), uploaded files are held purely in ephemeral `/tmp` memory for the duration of the request and immediately unlinked after extraction.

### 4. Sandboxed Code Execution
- Student coding solutions are isolated from the main application process.
- Execution runs via `python -I` (isolated mode) with empty system environment blocks.
- Execution hooks (`sys.addaudithook`) explicitly block OS calls: socket creation, filesystem writes outside scratch, process spawning (`subprocess`, `os.system`), and module tampering.
- Hard time caps kill runaway loops or denial-of-service attempts within $5$ seconds.

### 5. Media & Cloud Storage Isolation
- Interview video recordings are uploaded directly from the backend to private Supabase Storage buckets using backend-only service-role credentials.
- The client browser never receives cloud storage master keys.
- Playback URLs are issued as short-lived (60-minute) cryptographic signed URLs, preventing unauthorized link sharing.

### 6. CORS & Header Hardening
- Strict Cross-Origin Resource Sharing (`CORS_ORIGINS`) prevents unauthorized external web domains from issuing cross-site authenticated requests.
- Custom middleware calculates and injects process timing headers (`X-Process-Time-Ms`) for observability without leaking internal server architecture details.

---

## 🧪 Testing

ARJUNA AI includes a comprehensive automated test suite covering pure business logic (scheduler, SRS mastery, scoring, sandbox) and integration API tests:

```bash
# Navigate to backend directory
cd backend

# Run the complete test suite
python -m pytest tests -v

# Run only unit/logic tests
python -m pytest tests/test_learning_logic.py -v

# Run integration tests against API endpoints
python -m pytest tests/test_learning_api.py -v
```

---

## 📄 License

This project is developed as an academic capstone and portfolio project. All rights reserved. Refer to repository configuration for licensing terms.

---

<div align="center">
<b>ARJUNA AI</b> — Empowering the next generation of engineers, leaders, and innovators with intelligent, personalized career acceleration.
</div>

