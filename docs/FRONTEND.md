# Frontend guide

Which screen uses which frontend feature or library. Code lives in `frontend/src`.

## Core stack (every page)
| What | Used for |
|---|---|
| React 18 + TypeScript + Vite | App, build, dev server |
| React Router | Routing (`App.tsx`) |
| Tailwind CSS (`styles/index.css`) | All styling and the theme |
| `lib/api.ts` (`request`) | The single API client: auth header, errors |
| `lib/auth.tsx` | Login session and toast notifications |
| Lucide | Icons |
| Recharts | Standard charts (`components/charts.tsx`) |

## Shared app shell (`components/layout.tsx`)
- Sidebar and top bar for every signed-in page.
- **Motion**: each page fades and slides in on navigation.
- **Guide assistant** (`components/Assistant.tsx`): floating photo button on every signed-in page. Shows a short tip when you open a page, and a chat box that takes you to the right tab. Keyword-based, no AI call. Photo is `public/assistant.webp` (`AVATAR_SRC` in the file).

## Tab by tab

### Landing, Login, Register (`pages/Landing.tsx`, `Auth.tsx`, `components/suits.tsx`, `Cinematic.tsx`)
- Cinematic dark theme, rotating quotes (`QuoteRotator`), animated headline, transitions into login and register.
- Hero: guide photo with a speech bubble that cycles the quotes.
- **GSAP + ScrollTrigger**: the guide drifts up as you scroll (transform only, never hides content).

### Onboarding (`pages/Onboarding.tsx`)
- Multi-step wizard with progress, resume upload.

### Student Dashboard (`pages/Dashboard.tsx`)
- Recharts: readiness and skill charts, skill radar.
- **React Flow** (`components/SkillMap.tsx`): interactive skill-gap map. Click a bubble to see the fix and a link to plan time in the Learning Hub.

### Interview Arena (`pages/InterviewArena.tsx`)
- **Recharts radar** on the report: category scores.
- **Monaco** (`components/CodeEditor.tsx`): "Write code" toggle with a language picker.
- **Wavesurfer.js** (`components/Waveform.tsx`): live microphone waveform while you dictate an answer.
- Browser speech recognition and speech synthesis for voice.

### AI Learning Hub (`pages/learning/*`, `components/learning/*`)
| Page | Features |
|---|---|
| Overview | Streak, recommendations, animated numbers (`components/fx.tsx`) |
| Planner | **FullCalendar** (`components/learning/PlanCalendar.tsx`): month and week views, drag a task to another day to reschedule (server `PATCH /learning/tasks/{id}`) |
| Materials | Rendered notes, diagrams (`Diagram.tsx`), Markdown |
| YouTube | Chapters, concepts, terminology, flashcards |
| My Notes | Notebook shelf with covers and lock (`Covers.tsx`, `Diary.tsx`), page-turn animation, **Tiptap** editor (`components/RichEditor.tsx`) that stores Markdown so search and version history keep working |
| Quizzes | **Monaco** for coding questions, Recharts breakdown, question navigator |
| Progress | Recharts, consistency heatmap, mastery |

### Dynamic Resume Builder (`pages/ResumeBuilder.tsx`, `lib/resume.ts`)
- Live preview is the server's PDF, shown in an iframe, so it matches the download exactly.
- Editor for every field, **drag to reorder** entries (browser drag and drop), swap an item for another from your profile, fit-on-one-page meter.
- PDF and Word are generated on the server, not in the browser.

### CareerVerse (`pages/CareerVerse.tsx`, `CareerStory.tsx`, `CareerInsights.tsx`, `CareerCompare.tsx`)
- Animated story scenes (CSS and SVG).
- Recharts: career fit radar, salary charts, demand gauge (`components/InsightCharts.tsx`).
- **ECharts** (`components/SalaryRange.tsx`): pay range by level, loaded on demand.

### Settings (`pages/Settings.tsx`)
- Forms built from `components/ui.tsx`.

## Libraries installed but not wired in
- **Spline** and **Rive**: not added. They need a 3D scene link and a `.riv` file.
- **dnd-kit**, **Sonner**, **Shiki**, **Mermaid**, **KaTeX**, **React Player**, **Tremor**: not installed. Planner and resume drag use plain browser drag and drop instead.

## Setup notes
- Install with `npm install --legacy-peer-deps` (the React plugin and Vite 8 have a peer conflict).
- After installing new packages, restart the dev server with `npm run dev -- --force`.
- Heavy libraries (Monaco, ECharts) load on demand. Monaco fetches its files from a CDN, so it needs internet.
- Shared building blocks: `components/ui.tsx` (buttons, cards, modal, fields), `components/fx.tsx` (animations, counters).

## Language support (Sarvam AI)
- A language picker sits in the top bar of every signed-in page (Hindi, Marathi, Gujarati, Bengali, Tamil, Telugu, Kannada, Malayalam, Punjabi, Odia and English).
- `lib/i18n.tsx` translates every visible piece of text, including AI-written content, through `POST /api/translate`. It never touches typed input, code editors or code blocks, and switching back to English restores the original text exactly.
- Each distinct string is translated once and cached in the browser and in the `translation_cache` table, so repeat views are instant and cost nothing.
- The key lives only in `backend/.env` as `SARVAM_API_KEY` (model: `SARVAM_TRANSLATE_MODEL`, default `mayura:v1`). Without it the picker reports that translation is not configured and the site stays in English.
- Teammates need `python -m alembic upgrade head` once for the cache table.
