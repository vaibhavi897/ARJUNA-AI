/** Typed client for the AI Learning Hub. All calls go through the shared `request`. */
import { API_BASE, getToken, request } from "./api";
import type { ReviewItem } from "../components/learning/QuizReview";

export type Category = "learn" | "practice" | "project" | "revision" | "assessment" | "milestone" | "rest";
export type TaskStatus = "pending" | "completed" | "partial" | "skipped" | "rescheduled";

export type Task = {
  id: number; plan_id: number; date: string; original_date: string; position: number; category: Category; phase: string | null; title: string;
  topic: string | null; subtopics: string[]; objectives: string[]; assignment: string | null; resources: { kind: string; name: string; search_query: string }[];
  est_minutes: number; difficulty: string | null; status: TaskStatus; progress_pct: number; actual_minutes: number | null; self_difficulty: number | null;
  notes: string | null; reschedule_count: number; locked: boolean; missed: boolean;
};
export type Day = { date: string; tasks: Task[]; minutes: number; done: number; total: number; rest: boolean; milestone: { id: number; title: string; week: number; completed: boolean } | null };
export type Plan = {
  id: number; version: number; status: string; summary: string | null; starting_level: string | null; start_date: string; end_date: string; model: string | null;
  skill_gap: { starting_level: string; coverage: Record<string, number>; matched_titles: string[]; missing_titles: string[]; explanation?: { summary: string; strengths: string[]; priority_gaps: string[]; advice: string[]; source: string }; dropped_units?: string[]; method?: string };
  phases: { key: string; title: string; start: string; end: string; tasks: number }[];
  goal: { id: number; target_role: string; duration_days: number; daily_hours: number; study_days: number[]; breaks: { start: string; end: string; reason: string }[]; focus_areas: string[]; target_companies: string[]; skip_topics: string[]; existing_knowledge: string | null };
  milestones: { id: number; week: number; title: string; description: string | null; phase: string | null; due: string; completed: boolean }[];
};
export type Track = { slug: string; title: string; category: string; description: string; topics: number; hours: number };
export type Rec = { id: string; kind: string; title: string; reason: string; action: { type: string; [k: string]: unknown } };
export type Overview = {
  has_plan: boolean; streak: { current: number; best: number; active_days: number };
  recent_quizzes: { id: number; topic: string; accuracy: number | null; score: number; max_score: number; at: string }[];
  weak_topics: { topic: string; mastery: number; status: string; status_label: string }[];
  upcoming_revisions: { topic: string; due: string; interval_days: number }[]; recommendations: Rec[];
  plan: null | { id: number; goal: string; starting_level: string; summary: string | null; start: string; end: string; day_number: number; total_days: number; completion_pct: number; tasks_done: number; tasks_total: number; week: { done: number; total: number }; today: Task[]; upcoming: Task[]; missed: number; next_milestone: { title: string; due: string } | null; phases: Plan["phases"] };
};

export type Section = { heading: string; body: string };
export type Material = {
  id: number; topic: string; level: string; depth: string; kind: string; parent_id: number | null; followups: { question: string; answer: string }[]; created_at: string | null;
  content: {
    title: string; summary: string; definitions: Section[]; explanation: Section[]; examples: Section[]; code_snippets: { title: string; language: string; code: string; explanation: string }[];
    formulas: Section[]; real_world_applications: string[]; common_mistakes: string[]; interview_relevance: string[]; practice_problems: { question: string; hint: string; answer: string }[];
    key_takeaways: string[]; revision_summary: string; sources: string[];
    nodes?: { id: string; label: string }[]; edges?: { source?: string; target?: string; from?: string; to?: string; label: string }[]; description?: string;
  };
};
export type Video = { id: number; video_id: string; url: string; title: string | null; channel: string | null; thumbnail: string | null; transcript_status: string; segments: number; reason?: string; needs_transcript?: boolean;
  summary: null | { overview: string; level?: string; topics?: string[]; prerequisites?: string[]; concepts?: { name: string; explanation: string; why_it_matters: string; timestamp_seconds: number | null }[]; terminology?: { term: string; definition: string }[]; applications?: { area: string; description: string }[]; tools_mentioned?: string[]; chapters: { title: string; start_seconds: number; summary: string; key_points: string[] }[]; key_concepts: string[]; examples: string[]; takeaways: string[]; flashcards: { front: string; back: string }[]; quiz: { question: string; options: string[]; answer_index: number; explanation: string }[] } };

export type NotebookCard = { id: number; title: string; cover_style: string; locked: boolean; pages: number; folder: string | null; description: string | null; tags: string[]; updated_at: string | null };
export type NbIndex = { notebook: { id: number; title: string; cover_style: string; locked: boolean; description: string | null; tags: string[] }; chapters: { id: number; title: string; position: number }[]; pages: { id: number; page_no: number; title: string; chapter_id: number | null; bookmarked: boolean; tags: string[]; source_type: string; updated_at: string | null }[] };
export type Page = { id: number; notebook_id: number; page_no: number; title: string; content: string; chapter_id: number | null; tags: string[]; bookmarked: boolean; source_type: string; updated_at: string | null };

export type Question = { id: number; position: number; qtype: string; difficulty: string; topic: string; subtopic: string | null; prompt: string; options: string[]; points: number; starter_code: string | null; entry_function: string | null; examples: { args: unknown[]; expected: unknown }[];
  answer_key?: Record<string, unknown>; explanation?: string | null };
export type Quiz = { id: number; topic: string; scope: string; status: string; config: Record<string, any>; time_limit_minutes: number | null; started_at: string; score: number | null; max_score: number | null; questions: Question[] };
export type Report = { session_id: number; topic: string; score: number; max_score: number; accuracy: number; time_taken_seconds: number; time_limit_minutes: number | null; overtime: boolean; questions: number; correct: number; ungraded: number;
  by_topic: { topic: string; accuracy: number; score: number; max: number }[]; by_subtopic: { topic: string; accuracy: number }[]; strong_areas: string[]; weak_areas: string[];
  incorrect: { question_id: number; position: number; qtype: string; difficulty: string; topic: string; subtopic: string | null; prompt: string; your_answer: any; score: number; points: number; correct: any; explanation: string | null; feedback: any }[];
  recommended_revisions: { topic: string; reason: string }[] };
export type Progress = {
  heatmap: { date: string; tasks: number }[]; weekly: { week: string; tasks: number }[]; streak: { current: number; best: number; active_days: number };
  quiz_trend: { id: number; topic: string; accuracy: number; at: string; scope: string }[]; mastery: { topic: string; score: number; status: string; status_label: string; attempts: number; signals: Record<string, number | null> }[];
  mastery_counts: Record<string, number>; assessment_history: { id: number; topic: string; scope: string; accuracy: number; score: number; max_score: number; seconds: number; at: string }[];
  revision: { tasks_total: number; tasks_done: number; topics_tracked: number; due_now: number }; milestones: { title: string; due: string; week: number; completed: boolean }[];
  phases: { key: string; title: string; done: number; total: number }[]; weak: string[]; improvement: { topic: string; first: number; latest: number; change: number; attempts: number }[]; status_labels: Record<string, string>;
};

const j = (body: unknown) => ({ method: "POST" as const, body });
const q = (o: Record<string, string | number | undefined | null>) => { const p = new URLSearchParams(); Object.entries(o).forEach(([k, v]) => v !== undefined && v !== null && v !== "" && p.set(k, String(v))); const s = p.toString(); return s ? `?${s}` : ""; };

export const lh = {
  overview: () => request<Overview>("/learning/overview"),
  progress: () => request<Progress>("/learning/progress"),
  personalization: () => request<{ policy: string; events_collected: number; feedback_collected: number; rl_min_events: number; rl_ready: boolean; note: string }>("/learning/personalization"),
  tracks: () => request<{ items: Track[] }>("/learning/tracks"),
  skillGap: (track: string, role: string) => request<{ starting_level: string; coverage: Record<string, number>; matched_titles: string[]; missing_titles: string[]; profile_has_data: boolean; method: string; explanation: NonNullable<Plan["skill_gap"]["explanation"]> }>(`/learning/skill-gap${q({ track, role })}`),
  activePlan: () => request<{ plan: Plan | null }>("/learning/plans/active"),
  createPlan: (body: unknown) => request<Plan>("/learning/plans", j(body)),
  calendar: (id: number, start: string, end: string, filter: string) => request<{ days: Day[] }>(`/learning/plans/${id}/calendar${q({ start, end, filter })}`),
  regenerate: (id: number, daily_minutes?: number) => request<{ replaced: number; created: number; kept: number; dropped_units: string[]; plan: Plan }>(`/learning/plans/${id}/regenerate${q({ daily_minutes })}`, { method: "POST" }),
  availability: (id: number, body: unknown) => request<{ plan: Plan }>(`/learning/plans/${id}/availability`, { method: "PUT", body }),
  adjustments: (id: number) => request<{ enough_data: boolean; notes: string[]; completion_rate?: number; suggested_daily_factor?: number }>(`/learning/plans/${id}/adjustments`),
  missed: (id: number) => request<{ missed: number; moves: { task_id: number; title: string; from: string; to: string }[]; overflow: { task_id: number; title: string }[]; significant: boolean; message?: string; deadline?: string }>(`/learning/plans/${id}/missed`),
  applyMissed: (id: number, confirm: boolean) => request<{ moved: number }>(`/learning/plans/${id}/missed/apply`, j({ confirm })),
  patchTask: (id: number, body: unknown) => request<Task>(`/learning/tasks/${id}`, { method: "PATCH", body }),
  materials: (qs = "") => request<{ items: { id: number; topic: string; level: string; depth: string; kind: string; created_at: string }[] }>(`/learning/materials${q({ q: qs })}`),
  material: (id: number) => request<Material>(`/learning/materials/${id}`),
  createMaterial: (body: unknown) => request<Material>("/learning/materials", j(body)),
  materialAction: (id: number, action: string) => request<Material>(`/learning/materials/${id}/action`, j({ action })),
  ask: (id: number, question: string) => request<{ question: string; answer: string }>(`/learning/materials/${id}/ask`, j({ question })),
  deleteMaterial: (id: number) => request<void>(`/learning/materials/${id}`, { method: "DELETE" }),
  videos: () => request<{ items: Video[] }>("/learning/youtube"),
  importVideo: (url: string, transcript?: string) => request<Video>("/learning/youtube", j({ url, transcript })),
  resummarise: (id: number) => request<Video>(`/learning/youtube/${id}/summarise`, { method: "POST" }),
  summariseVideo: (id: number, transcript: string) => request<Video>(`/learning/youtube/${id}/summarise`, j({ url: "https://youtu.be/xxxxxxxxxxx", transcript })),
  notebooks: () => request<{ items: NotebookCard[]; covers: string[] }>("/learning/notebooks"),
  createNotebook: (body: unknown) => request<NotebookCard>("/learning/notebooks", j(body)),
  patchNotebook: (id: number, body: unknown, t?: string) => nb<NotebookCard>(`/learning/notebooks/${id}`, "PATCH", body, t),
  deleteNotebook: (id: number, t?: string) => nb<void>(`/learning/notebooks/${id}`, "DELETE", undefined, t),
  unlock: (id: number, password: string) => request<{ token: string | null; expires_in: number }>(`/learning/notebooks/${id}/unlock`, j({ password })),
  setLock: (id: number, body: unknown) => request<NotebookCard>(`/learning/notebooks/${id}/lock`, { method: "PUT", body }),
  nbIndex: (id: number, t?: string) => nb<NbIndex>(`/learning/notebooks/${id}/index`, "GET", undefined, t),
  page: (id: number, no: number, t?: string) => nb<Page>(`/learning/notebooks/${id}/pages/${no}`, "GET", undefined, t),
  addPage: (id: number, body: unknown, t?: string) => nb<Page>(`/learning/notebooks/${id}/pages`, "POST", body, t),
  saveVideoNotes: (importId: number, content: string) => request<{ saved: boolean; notebook_id?: number; notebook?: string; page_no?: number }>(`/learning/youtube/${importId}/notes`, { method: "PUT", body: { content } }),
  savePage: (id: number, no: number, body: unknown, t?: string) => nb<Page>(`/learning/notebooks/${id}/pages/${no}`, "PATCH", body, t),
  deletePage: (id: number, no: number, t?: string) => nb<void>(`/learning/notebooks/${id}/pages/${no}`, "DELETE", undefined, t),
  history: (id: number, no: number, t?: string) => nb<{ items: { id: number; title: string; content: string; saved_at: string }[] }>(`/learning/notebooks/${id}/pages/${no}/history`, "GET", undefined, t),
  restore: (id: number, no: number, v: number, t?: string) => nb<Page>(`/learning/notebooks/${id}/pages/${no}/restore/${v}`, "POST", undefined, t),
  search: (id: number, qs: string, t?: string) => nb<{ items: { page_no: number; title: string; snippet: string }[] }>(`/learning/notebooks/${id}/search${q({ q: qs })}`, "GET", undefined, t),
  addChapter: (id: number, title: string, t?: string) => nb<{ id: number; title: string; position: number }>(`/learning/notebooks/${id}/chapters`, "POST", { title }, t),
  renameChapter: (id: number, cid: number, title: string, t?: string) => nb<{ id: number; title: string }>(`/learning/notebooks/${id}/chapters/${cid}`, "PATCH", { title }, t),
  saveMaterial: (id: number, mid: number, t?: string) => nb<Page>(`/learning/notebooks/${id}/save-material/${mid}`, "POST", {}, t),
  saveVideo: (id: number, vid: number, t?: string) => nb<Page>(`/learning/notebooks/${id}/save-video/${vid}`, "POST", {}, t),
  upload: async (id: number, file: File, t?: string) => {
    const fd = new FormData(); fd.append("file", file);
    return nb<{ pages: Page[] }>(`/learning/notebooks/${id}/upload`, "POST", undefined, t, fd);
  },
  quizzes: () => request<{ items: { id: number; topic: string; scope: string; status: string; accuracy: number | null; score: number | null; max_score: number | null; questions: number; started_at: string }[] }>("/learning/quizzes"),
  createQuiz: (body: unknown) => request<Quiz>("/learning/quizzes", j(body)),
  quiz: (id: number) => request<Quiz>(`/learning/quizzes/${id}`),
  submitQuiz: (id: number, answers: Record<number, unknown>) => request<Report>(`/learning/quizzes/${id}/submit`, j({ answers })),
  results: (id: number) => request<{ report: Report; quiz: Quiz; review: ReviewItem[] }>(`/learning/quizzes/${id}/results`),
  retryQuiz: (id: number) => request<Quiz>(`/learning/quizzes/${id}/retry`, { method: "POST" }),
  revisions: () => request<{ items: { topic: string; due: string; interval_days: number; ease: number; repetitions: number; lapses: number; overdue: boolean }[] }>("/learning/revisions"),
  settings: () => request<{ interval_scale: number; preferred_depth: string }>("/learning/settings"),
  putSettings: (body: unknown) => request<{ interval_scale: number; preferred_depth: string }>("/learning/settings", { method: "PUT", body }),
  feedback: (body: unknown) => request<{ ok: boolean }>("/learning/feedback", j(body)),
};

/** Notebook calls carry the unlock token header; uploads use multipart. */
async function nb<T>(path: string, method: "GET" | "POST" | "PATCH" | "DELETE", body?: unknown, token?: string, form?: FormData): Promise<T> {
  if (!token && !form) return request<T>(path, { method, body });
  const headers: Record<string, string> = { Accept: "application/json" };
  const auth = getToken();
  if (auth) headers.Authorization = `Bearer ${auth}`;
  if (token) headers["X-Notebook-Token"] = token;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_BASE}${path}`, { method, headers, body: form ?? (body !== undefined ? JSON.stringify(body) : undefined) });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const { ApiError } = await import("./api");
    throw new ApiError(res.status, (data && data.detail) || `Request failed (${res.status})`);
  }
  return data as T;
}
