/**
 * Single API client for the whole app.
 *
 * Everything goes through `request`, so the auth header, JSON handling and
 * error normalisation live in exactly one place. There is no second copy of
 * student data anywhere in the frontend: screens fetch from here.
 */

export const TOKEN_KEY = "arjuna.access_token";
const API_BASE = "/api";

export class ApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage can be blocked; the session simply will not persist */
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  formData?: FormData;
  signal?: AbortSignal;
};

/** Fired when the server rejects our token, so the app can sign the user out. */
const unauthorizedListeners = new Set<() => void>();

export function onUnauthorized(listener: () => void): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, signal } = options;
  const headers: Record<string, string> = { Accept: "application/json" };

  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal,
    });
  } catch (error) {
    if ((error as Error)?.name === "AbortError") throw error;
    throw new ApiError(
      0,
      "Could not reach the Arjuna AI server. Check that the backend is running on port 8000."
    );
  }

  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => null);

  if (!response.ok) {
    if (response.status === 401) unauthorizedListeners.forEach((fn) => fn());

    const fieldErrors: Record<string, string> = {};
    if (payload && typeof payload === "object" && Array.isArray((payload as any).errors)) {
      for (const item of (payload as any).errors) {
        if (item?.field) fieldErrors[item.field] = item.message ?? "Invalid value";
      }
    }
    const detail =
      (payload && typeof payload === "object" && (payload as any).detail) ||
      (typeof payload === "string" && payload) ||
      `Request failed (${response.status})`;

    throw new ApiError(
      response.status,
      typeof detail === "string" ? detail : "Request failed",
      fieldErrors
    );
  }

  return payload as T;
}

export const api = {
  // ---- auth ----
  register: (body: unknown) => request<AuthResponse>("/auth/register", { method: "POST", body }),
  login: (body: unknown) => request<AuthResponse>("/auth/login", { method: "POST", body }),
  me: () => request<User>("/auth/me"),
  logout: () => request<{ message: string }>("/auth/logout", { method: "POST" }),
  availability: (field: "email" | "username", value: string) =>
    request<{ field: string; value: string; available: boolean }>(
      `/auth/availability?field=${field}&value=${encodeURIComponent(value)}`
    ),
  changePassword: (body: unknown) =>
    request<{ message: string }>("/auth/change-password", { method: "POST", body }),

  // ---- catalogue ----
  domains: () => request<CareerDomain[]>("/catalog/domains"),
  roles: () => request<JobRole[]>("/catalog/roles"),
  roleRubric: (slug: string) => request<any>(`/catalog/roles/${slug}`),
  skills: (query?: string) =>
    request<SkillOption[]>(`/catalog/skills${query ? `?q=${encodeURIComponent(query)}` : ""}`),

  // ---- onboarding ----
  onboardingStatus: () => request<OnboardingStatus>("/onboarding/status"),
  saveStep: (key: string, body: unknown) =>
    request<StepResult>(`/onboarding/${key}`, { method: "POST", body }),
  completeOnboarding: () => request<StepResult>("/onboarding/complete", { method: "POST" }),

  // ---- profile ----
  profile: () => request<FullProfile>("/profile"),
  updateSection: (section: string, body: unknown) =>
    request<ActionResult>(`/profile/${section}`, { method: "PUT", body }),

  // ---- resume ----
  resumeLimits: () => request<{ allowed_extensions: string[]; max_size_mb: number }>("/resume/limits"),
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ message: string; recalculated_roles: string[]; review: ResumeReview }>(
      "/resume/upload",
      { method: "POST", formData: form }
    );
  },
  resumeReview: () => request<ResumeReview>("/resume/review"),
  importResume: (body: unknown) =>
    request<ActionResult>("/resume/import", { method: "POST", body }),
  skipResume: () => request<ActionResult>("/resume/skip", { method: "POST" }),

  // ---- dashboard ----
  dashboard: () => request<Dashboard>("/dashboard"),
  roleDetail: (slug: string) => request<RoleDetail>(`/dashboard/roles/${slug}`),
  recalculate: () => request<ActionResult>("/dashboard/recalculate", { method: "POST" }),
  roadmap: () => request<Roadmap>("/roadmap"),
  updateTask: (id: number, status: string) =>
    request<ActionResult>(`/roadmap/tasks/${id}`, { method: "PATCH", body: { status } }),
  activity: (limit = 30) => request<{ items: Activity[] }>(`/activity?limit=${limit}`),

  // ---- settings ----
  settings: () => request<StudentSettings>("/settings"),
  updateSettings: (body: unknown) =>
    request<StudentSettings>("/settings", { method: "PUT", body }),
  updateAccount: (body: unknown) =>
    request<ActionResult>("/settings/account", { method: "PUT", body }),
  // ---- Interview Arena ----
  interviewHistory: () => request<InterviewSession[]>("/interviews"),
  interviewSession: (id: number) => request<InterviewSession>(`/interviews/${id}`),
  startInterview: (body: unknown) => request<InterviewSession>("/interviews", { method: "POST", body }),
  answerInterview: (id: number, answer: string) => request<InterviewAnswerResult>(`/interviews/${id}/answer`, { method: "POST", body: { answer } }),
  endInterview: (id: number, integrity_signals: IntegritySignal[]) => request<InterviewSession>(`/interviews/${id}/end`, { method: "POST", body: { integrity_signals } }),
};

// ---------------------------------------------------------------------------
// Types mirroring the backend schemas
// ---------------------------------------------------------------------------
export type User = {
  id: number;
  full_name: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  is_demo: boolean;
  onboarding_step: number;
  onboarding_completed: boolean;
  last_login_at: string | null;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
  next_route: string;
};

export type SkillOption = {
  id: number;
  name: string;
  slug: string;
  category: string;
  is_custom: boolean;
};

export type JobRole = {
  id: number;
  name: string;
  slug: string;
  short_label: string | null;
  description: string | null;
  domain_id: number;
  domain_name: string;
  domain_slug: string;
  display_order: number;
};

export type CareerDomain = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  icon: string | null;
  accent_color: string | null;
  display_order: number;
  roles: JobRole[];
};

export type OnboardingStep = {
  step: number;
  key: string;
  title: string;
  subtitle: string;
  is_complete: boolean;
  is_optional: boolean;
  companion_message: string;
};

export type OnboardingStatus = {
  current_step: number;
  total_steps: number;
  completed: boolean;
  percent_complete: number;
  profile_completion: number;
  steps: OnboardingStep[];
  next_route: string;
};

export type StepResult = {
  message: string;
  step: number;
  next_step: number;
  completed: boolean;
  profile_completion: number;
  companion_message: string;
  recalculated_roles: string[];
  data: Record<string, any> | null;
};

export type ActionResult = {
  message: string;
  recalculated_roles: string[];
  data: Record<string, any> | null;
};

export type StudentSkill = {
  id: number;
  skill_id: number;
  name: string;
  slug: string;
  category: string;
  proficiency: "beginner" | "intermediate" | "advanced";
  years_of_experience: number | null;
  source: string;
  evidence_count: number;
  is_evidence_backed: boolean;
  notes: string | null;
};

export type ProjectEntry = {
  id: number;
  title: string;
  description: string | null;
  contribution: string | null;
  category: string | null;
  duration_months: number | null;
  start_date: string | null;
  end_date: string | null;
  is_ongoing: boolean;
  team_size: number | null;
  github_url: string | null;
  live_url: string | null;
  source: string;
  technologies: string[];
};

export type AcademicEntry = {
  id: number;
  level: string;
  institution: string;
  board_or_university: string | null;
  degree_or_program: string | null;
  specialization: string | null;
  score: number | null;
  score_type: string | null;
  start_year: number | null;
  end_year: number | null;
  is_current: boolean;
  achievements: string | null;
  relevant_coursework: string[];
};

export type ExperienceEntry = {
  id: number;
  experience_type: string;
  organization: string;
  title: string;
  description: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  duration_months: number | null;
  skills_used: string[];
  source: string;
};

export type CertificationEntry = {
  id: number;
  name: string;
  issuer: string | null;
  issue_date: string | null;
  expiry_date: string | null;
  credential_id: string | null;
  credential_url: string | null;
  related_skills: string[];
  source: string;
};

export type AchievementEntry = {
  id: number;
  title: string;
  description: string | null;
  category: string;
  scope: string | null;
  date_awarded: string | null;
  source: string;
};

export type FullProfile = {
  user: Record<string, any>;
  profile: {
    phone: string | null;
    location: string | null;
    headline: string | null;
    bio: string | null;
    college: string | null;
    degree: string | null;
    branch: string | null;
    graduation_year: number | null;
    current_academic_year: string | null;
    cgpa: number | null;
    cgpa_scale: number;
    github_url: string | null;
    linkedin_url: string | null;
    portfolio_url: string | null;
    other_links: { label?: string; url?: string }[];
    profile_completion: number;
    completion_breakdown: Record<string, any>;
  };
  academics: AcademicEntry[];
  skills: StudentSkill[];
  projects: ProjectEntry[];
  experiences: ExperienceEntry[];
  certifications: CertificationEntry[];
  achievements: AchievementEntry[];
  preferences: {
    role_id: number;
    role_name: string;
    role_slug: string;
    domain_id: number;
    domain_name: string;
    priority: number;
    is_primary: boolean;
  }[];
  resume: {
    id: number;
    original_filename: string;
    file_extension: string;
    file_size_bytes: number;
    parse_status: string;
    parse_error: string | null;
    quality_score: number | null;
    reviewed_by_student: boolean;
    uploaded_at: string;
  } | null;
};

export type ResumeReview = {
  resume_id: number;
  parse_status: string;
  parse_error: string | null;
  quality?: {
    score: number;
    checks: { key: string; label: string; earned: number; possible: number; passed: boolean; detail: string }[];
    strengths: string[];
    improvements: string[];
    sections_found: string[];
    sections_missing: string[];
    word_count: number;
  } | null;
  stats?: Record<string, any>;
  sections_found?: string[];
  education?: Record<string, any>[];
  suggestions: {
    contact: Record<string, { value: string | null; current: string | null; fills_blank: boolean }>;
    skills: { name: string; already_in_profile: boolean; suggested_proficiency: string }[];
    projects: { title: string; description?: string; technologies?: string[]; already_in_profile: boolean }[];
    experience: { title: string; organization: string; experience_type: string; already_in_profile: boolean }[];
    certifications: { name: string; issuer?: string | null; year?: number | null; already_in_profile: boolean }[];
    achievements: { title: string; category: string; year?: number | null; already_in_profile: boolean }[];
  } | null;
  notice?: string;
};

export type RoleScore = {
  role_id: number;
  role_slug: string;
  role_name: string;
  short_label: string | null;
  domain_id: number;
  domain_name: string;
  domain_slug: string;
  accent_color: string | null;
  score: number;
  band: string;
  previous_score: number | null;
  score_delta: number | null;
  is_preferred: boolean;
  is_primary: boolean;
  computed_at: string;
  matched_required: number;
  total_required: number;
  engine_version: string;
  ai_enriched: boolean;
};

export type RoadmapTask = {
  id: number;
  title: string;
  reason: string;
  priority: "high" | "medium" | "low";
  suggested_duration: string | null;
  expected_improvement_area: string | null;
  expected_score_gain: number | null;
  action_type: string;
  status: "pending" | "in_progress" | "completed";
  completed_at: string | null;
  related_skill: string | null;
  role_name: string | null;
  role_slug: string | null;
};

export type Roadmap = {
  generated_at: string | null;
  generator: string;
  total_tasks: number;
  completed_tasks: number;
  completion_percent: number;
  tasks: RoadmapTask[];
};

export type Activity = {
  id: number;
  activity_type: string;
  title: string;
  description: string | null;
  icon: string | null;
  details: Record<string, any>;
  created_at: string;
};

export type Dashboard = {
  generated_at: string;
  welcome: {
    full_name: string;
    first_name: string;
    username: string;
    email: string;
    college: string | null;
    degree: string | null;
    branch: string | null;
    graduation_year: number | null;
    current_academic_year: string | null;
    cgpa: number | null;
    cgpa_scale: number;
    profile_completion: number;
    completion_breakdown: Record<string, any>;
    career_interests: string[];
    greeting: string;
    greeting_source: string;
    member_since: string;
    last_assessment_at: string | null;
  };
  readiness: {
    has_assessments: boolean;
    overall_score: number | null;
    overall_band: string | null;
    last_assessed_at: string | null;
    engine_version: string | null;
    roles: RoleScore[];
    preferred_roles: RoleScore[];
    best_matches: RoleScore[];
    domain_averages: {
      domain_slug: string;
      domain_name: string;
      accent_color: string | null;
      average_score: number;
      best_score: number;
      role_count: number;
      best_role: string;
    }[];
  };
  strengths: Record<string, any>[];
  improvements: Record<string, any>[];
  skills: {
    total_skills: number;
    evidence_backed: number;
    claimed_only: number;
    by_category: { category: string; label: string; count: number; evidence_backed: number; skills: any[] }[];
    by_proficiency: { level: string; count: number }[];
    technical_vs_business: { label: string; count: number }[];
    top_skills: { name: string; category: string; proficiency: string; evidence_count: number; score: number }[];
    radar: { category: string; label: string; value: number; count: number }[];
    role_gaps: {
      skill_name: string;
      status: string;
      importance: string;
      expected_proficiency: string;
      student_proficiency: string | null;
      points_lost: number;
      recommendation: string | null;
    }[];
  };
  roadmap: Roadmap;
  resume_insights: {
    has_resume: boolean;
    resume: Record<string, any> | null;
    quality_score: number | null;
    strengths: string[];
    improvements: string[];
    missing_keywords: { keyword: string; present: boolean }[];
    identified_skills: string[];
    sections_found: string[];
    sections_missing: string[];
    word_count: number | null;
    parse_status: string | null;
  };
  portfolio: {
    projects: number;
    internships: number;
    work_experience: number;
    positions_of_responsibility: number;
    certifications: number;
    achievements: number;
    extracurriculars: number;
    total_experience_months: number;
    links: { github: string | null; linkedin: string | null; portfolio: string | null; others: any[] };
    recent_projects: { id: number; title: string; category: string | null; technologies: string[]; has_link: boolean }[];
  };
  career_fit: {
    role_id: number;
    role_slug: string;
    role_name: string;
    domain_name: string;
    score: number;
    band: string;
    fit_label: string;
    why_good_fit: string[];
    whats_missing: string[];
  }[];
  progress: {
    series: { role_slug: string; role_name: string; points: { at: string; score: number; band: string; version: number }[] }[];
    overall_series: { at: string; score: number; roles: number }[];
    assessment_count: number;
    first_assessed_at: string | null;
    last_assessed_at: string | null;
    best_improvement: { role_name: string; role_slug: string; delta: number; from_score: number; to_score: number } | null;
    completed_roadmap_tasks: { title: string; completed_at: string | null; area: string | null; priority: string }[];
  };
  recent_activity: Activity[];
  ai_insights: { kind: string; title: string; body: string; severity: string }[];
  ai_mode: string;
};

export type RoleDetail = {
  role: Record<string, any>;
  score: number;
  band: string;
  previous_score: number | null;
  score_delta: number | null;
  computed_at: string;
  engine_version: string;
  ai_enriched: boolean;
  weights: Record<string, number>;
  breakdowns: {
    component: string;
    label: string;
    weight: number;
    raw_ratio: number;
    points_earned: number;
    points_possible: number;
    explanation: string;
    details: Record<string, any>;
  }[];
  strengths: Record<string, any>[];
  improvements: Record<string, any>[];
  insights: Record<string, any>[];
  match_summary: Record<string, any>;
  skill_gaps: {
    skill_id: number;
    skill_name: string;
    status: string;
    importance: string;
    expected_proficiency: string;
    student_proficiency: string | null;
    is_evidence_backed: boolean;
    points_lost: number;
    recommendation: string | null;
  }[];
  skill_comparison: {
    skill_name: string;
    category: string;
    importance: string;
    expected_proficiency: string;
    student_proficiency: string | null;
    has_skill: boolean;
    is_evidence_backed: boolean;
    evidence_count: number;
    expected_value: number;
    student_value: number;
  }[];
  history: { at: string; score: number; band: string; version: number; trigger: string | null }[];
};

export type StudentSettings = {
  email_notifications: boolean;
  weekly_progress_digest: boolean;
  roadmap_reminders: boolean;
  profile_visibility: string;
  theme: string;
  auto_recalculate_scores: boolean;
};

export type IntegritySignal = { type: string; at: string; detail?: string };
export type InterviewEvaluation = {
  score?: number;
  feedback?: string;
  strengths?: string[];
  improvements?: string[];
  better_answer?: string;
  explanation?: string;
};
export type InterviewMessage = {
  role: "interviewer" | "student";
  text: string;
  question?: string;
  category?: string;
  persona?: string;
  at?: string;
  evaluation?: InterviewEvaluation;
};
export type InterviewSession = {
  id: number;
  domain: string;
  status: "active" | "completed";
  started_at: string;
  ended_at: string | null;
  attempted_count: number;
  report: Record<string, any> | null;
  personas: string[];
  focus: Record<string, number>;
  transcript: InterviewMessage[];
  integrity_signals: IntegritySignal[];
  consent_media?: boolean;
};
export type InterviewAnswerResult = {
  session: InterviewSession;
  evaluation: InterviewEvaluation;
  closing: boolean;
  message?: string | null;
};
