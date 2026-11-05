/**
 * Seven-step onboarding wizard.
 *
 * Each step POSTs on its own, so nothing is lost between steps and an
 * interrupted session resumes at the first incomplete step. Existing values are
 * loaded from the profile endpoint, which means re-visiting a step edits the
 * stored data rather than starting over.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Award,
  BookOpen,
  Briefcase,
  CheckCircle2,
  FileText,
  FolderGit2,
  GraduationCap,
  Link2,
  Loader2,
  Plus,
  Sparkles,
  Target,
  Upload,
  UserCircle2,
  Zap,
} from "lucide-react";
import { Companion, MobileProgress, StepRail } from "../components/Companion";
import { Logo } from "../components/layout";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  EmptyState,
  ErrorState,
  Field,
  InlineNote,
  PageLoader,
  RepeaterItem,
  Select,
  TagInput,
  TextArea,
  TextInput,
} from "../components/ui";
import {
  ApiError,
  api,
  type AcademicEntry,
  type CareerDomain,
  type FullProfile,
  type OnboardingStatus,
  type ResumeReview,
  type SkillOption,
} from "../lib/api";
import { useAuth, useToast } from "../lib/auth";
import {
  ACADEMIC_LEVEL_LABELS,
  EXPERIENCE_TYPE_LABELS,
  PROFICIENCIES,
  SKILL_CATEGORY_LABELS,
  cn,
  titleCase,
} from "../lib/utils";

const CURRENT_YEAR = new Date().getFullYear();

const WHY_COPY: Record<number, string[]> = {
  1: [
    "Graduation year and academic year decide which placement cycle you are compared against.",
    "CGPA is optional, but several finance and consulting rubrics screen on it.",
  ],
  2: [
    "Prior qualifications and coursework feed the Academic Profile component.",
    "Relevant coursework also counts towards domain knowledge for technical roles.",
  ],
  3: [
    "Listing a skill is a claim. Using it in a project or internship turns it into evidence.",
    "Claimed-only skills earn 55% of the credit an evidence-backed skill earns.",
  ],
  4: [
    "Projects carry the largest practical-evidence weight in nearly every rubric.",
    "Technologies you list here are matched against each role's required skills.",
  ],
  5: [
    "Internships drive the experience component; certifications and achievements have their own weights.",
    "Positions of responsibility count, but less than hands-on work experience.",
  ],
  6: [
    "Resume quality is scored on sections, bullets, action verbs and quantified impact.",
    "Nothing from your resume is imported until you tick it - your typed data wins.",
  ],
  7: [
    "Each role you select is scored against its own rubric, with its own weights.",
    "All active roles are still scored, so you can discover unexpectedly good matches.",
  ],
};

const ACADEMIC_YEARS = [
  "1st Year",
  "2nd Year",
  "3rd Year",
  "4th Year",
  "5th Year",
  "Final Year",
  "Graduated",
];

const PROJECT_CATEGORIES = [
  "Web Development",
  "Backend",
  "Full Stack",
  "Machine Learning",
  "Data Science",
  "Data Analytics",
  "AI",
  "Business Intelligence",
  "Finance",
  "Valuation",
  "Equity Research",
  "Risk",
  "Compliance",
  "Consulting",
  "Strategy",
  "Product",
  "Operations",
  "Process",
  "Systems",
  "Electronics",
  "Other",
];

type StepKey =
  | "personal"
  | "academics"
  | "skills"
  | "projects"
  | "experience"
  | "resume"
  | "preferences";

const STEP_KEYS: Record<number, StepKey> = {
  1: "personal",
  2: "academics",
  3: "skills",
  4: "projects",
  5: "experience",
  6: "resume",
  7: "preferences",
};

const STEP_ICONS: Record<number, React.ReactNode> = {
  1: <UserCircle2 size={18} />,
  2: <GraduationCap size={18} />,
  3: <Zap size={18} />,
  4: <FolderGit2 size={18} />,
  5: <Briefcase size={18} />,
  6: <FileText size={18} />,
  7: <Target size={18} />,
};

export default function Onboarding() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const { user, refreshUser } = useAuth();
  const { push } = useToast();

  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [profile, setProfile] = useState<FullProfile | null>(null);
  const [domains, setDomains] = useState<CareerDomain[]>([]);
  const [skillOptions, setSkillOptions] = useState<SkillOption[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [celebrating, setCelebrating] = useState(false);
  const [finishing, setFinishing] = useState(false);

  const requestedStep = Number(params.get("step"));
  const [step, setStep] = useState(
    Number.isFinite(requestedStep) && requestedStep >= 1 && requestedStep <= 7 ? requestedStep : 1
  );

  const load = useCallback(
    async (options?: { silent?: boolean }) => {
      try {
        const [statusData, profileData] = await Promise.all([
          api.onboardingStatus(),
          api.profile(),
        ]);
        setStatus(statusData);
        setProfile(profileData);
        setLoadError(null);
        if (!options?.silent) {
          const target = Number(params.get("step"));
          if (!target || target < 1 || target > 7) setStep(statusData.current_step);
        }
        return statusData;
      } catch (error) {
        setLoadError(
          error instanceof ApiError ? error.message : "Could not load your onboarding progress."
        );
        return null;
      }
    },
    [params]
  );

  useEffect(() => {
    load();
    api.domains().then(setDomains).catch(() => setDomains([]));
    api.skills().then(setSkillOptions).catch(() => setSkillOptions([]));
  }, [load]);

  useEffect(() => {
    setParams(new URLSearchParams({ step: String(step) }), { replace: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [step, setParams]);

  const definition = useMemo(
    () => status?.steps.find((item) => item.step === step),
    [status, step]
  );

  const afterSave = async (message: string, recalculated: string[]) => {
    setCelebrating(true);
    window.setTimeout(() => setCelebrating(false), 2600);
    push({
      title: message,
      description: recalculated.length
        ? `${recalculated.length} role score(s) refreshed.`
        : undefined,
      variant: "success",
    });
    const fresh = await load({ silent: true });
    await refreshUser();
    return fresh;
  };

  const saveStep = async (key: StepKey, body: unknown, advance = true) => {
    setSaving(true);
    try {
      const result = await api.saveStep(key, body);
      const fresh = await afterSave(result.message, result.recalculated_roles);
      if (advance) {
        const next = step < 7 ? step + 1 : 7;
        setStep(fresh ? Math.max(next, Math.min(fresh.current_step, 7)) === 0 ? next : next : next);
      }
      return true;
    } catch (error) {
      push({
        title: "Could not save this step",
        description: error instanceof ApiError ? error.message : "Please try again.",
        variant: "error",
      });
      return false;
    } finally {
      setSaving(false);
    }
  };

  const finish = async () => {
    setFinishing(true);
    try {
      const result = await api.completeOnboarding();
      await refreshUser();
      push({
        title: "Onboarding complete",
        description: `${result.recalculated_roles.length} roles assessed.`,
        variant: "success",
      });
      navigate("/app/dashboard", { replace: true });
    } catch (error) {
      push({
        title: "Could not finish onboarding",
        description: error instanceof ApiError ? error.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setFinishing(false);
    }
  };

  if (loadError) {
    return (
      <div className="mx-auto max-w-xl px-4 py-20">
        <ErrorState message={loadError} onRetry={() => load()} />
      </div>
    );
  }

  if (!status || !profile) return <PageLoader label="Loading your onboarding" />;

  const allRequiredDone = status.steps
    .filter((item) => !item.is_optional)
    .every((item) => item.is_complete);

  const sharedProps = {
    profile,
    skillOptions,
    domains,
    saving,
    onSaved: afterSave,
    goTo: setStep,
  };

  return (
    <div className="min-h-screen bg-surface-sunken">
      <header className="sticky top-0 z-20 border-b border-line bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3.5 sm:px-6 lg:px-8">
          <Logo />
          <div className="flex items-center gap-3">
            <Badge tone="neutral" className="hidden sm:inline-flex">
              {status.percent_complete}% of required steps
            </Badge>
            {user?.onboarding_completed ? (
              <Button size="sm" variant="outline" onClick={() => navigate("/app/dashboard")}>
                Back to dashboard
              </Button>
            ) : null}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mb-5 space-y-4">
          <MobileProgress percent={status.percent_complete} label="Onboarding progress" />
          <StepRail steps={status.steps} current={step} onSelect={setStep} />
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="min-w-0 space-y-5">
            <Card className="p-5 sm:p-6">
              <div className="mb-6 flex items-start gap-3 border-b border-line pb-5">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-forest-800 text-white">
                  {STEP_ICONS[step]}
                </span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="font-display text-xl font-bold">{definition?.title}</h1>
                    {definition?.is_optional ? <Badge tone="neutral">Optional</Badge> : null}
                    {definition?.is_complete ? (
                      <Badge tone="brand">
                        <CheckCircle2 size={11} /> Saved
                      </Badge>
                    ) : null}
                  </div>
                  <p className="mt-0.5 text-sm text-ink-500">{definition?.subtitle}</p>
                </div>
              </div>

              {step === 1 ? (
                <PersonalStep {...sharedProps} onSubmit={(body) => saveStep("personal", body)} />
              ) : null}
              {step === 2 ? (
                <AcademicsStep {...sharedProps} onSubmit={(body) => saveStep("academics", body)} />
              ) : null}
              {step === 3 ? (
                <SkillsStep {...sharedProps} onSubmit={(body) => saveStep("skills", body)} />
              ) : null}
              {step === 4 ? (
                <ProjectsStep {...sharedProps} onSubmit={(body) => saveStep("projects", body)} />
              ) : null}
              {step === 5 ? (
                <ExperienceStep {...sharedProps} onSubmit={(body) => saveStep("experience", body)} />
              ) : null}
              {step === 6 ? <ResumeStep {...sharedProps} /> : null}
              {step === 7 ? (
                <PreferencesStep
                  {...sharedProps}
                  onSubmit={(body) => saveStep("preferences", body, false)}
                />
              ) : null}
            </Card>

            {/* Step navigation */}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <Button
                variant="ghost"
                icon={<ArrowLeft size={16} />}
                onClick={() => setStep((current) => Math.max(1, current - 1))}
                disabled={step === 1}
              >
                Previous
              </Button>

              <div className="flex items-center gap-2">
                {step < 7 ? (
                  <Button
                    variant="outline"
                    onClick={() => setStep((current) => Math.min(7, current + 1))}
                    icon={<ArrowRight size={16} />}
                  >
                    {definition?.is_optional ? "Skip for now" : "Next step"}
                  </Button>
                ) : null}

                {allRequiredDone ? (
                  <Button
                    size="md"
                    loading={finishing}
                    onClick={finish}
                    icon={<Sparkles size={16} />}
                  >
                    {user?.onboarding_completed
                      ? "Re-run my assessment"
                      : "Finish and generate my scores"}
                  </Button>
                ) : null}
              </div>
            </div>

            {!allRequiredDone ? (
              <InlineNote tone="info">
                Still to complete:{" "}
                {status.steps
                  .filter((item) => !item.is_optional && !item.is_complete)
                  .map((item) => item.title)
                  .join(", ")}
                . Your scores are generated once these are saved.
              </InlineNote>
            ) : null}
          </div>

          <Companion
            className="lg:sticky lg:top-24 lg:self-start"
            message={definition?.companion_message ?? ""}
            stepTitle={definition?.title ?? ""}
            stepNumber={step}
            totalSteps={status.total_steps}
            percent={status.percent_complete}
            celebrating={celebrating}
            why={WHY_COPY[step]}
          />
        </div>
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared step props
// ---------------------------------------------------------------------------
type StepProps = {
  profile: FullProfile;
  skillOptions: SkillOption[];
  domains: CareerDomain[];
  saving: boolean;
  onSaved: (message: string, recalculated: string[]) => Promise<OnboardingStatus | null>;
  goTo: (step: number) => void;
};

function StepActions({
  saving,
  label = "Save and continue",
  onClick,
}: {
  saving: boolean;
  label?: string;
  onClick?: () => void;
}) {
  return (
    <div className="flex justify-end border-t border-line pt-5">
      <Button type="submit" loading={saving} onClick={onClick} icon={<ArrowRight size={16} />}>
        {label}
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 1 - personal
// ---------------------------------------------------------------------------
function PersonalStep({
  profile,
  saving,
  onSubmit,
}: StepProps & { onSubmit: (body: unknown) => Promise<boolean> }) {
  const [form, setForm] = useState({
    full_name: String(profile.user.full_name ?? ""),
    email: String(profile.user.email ?? ""),
    phone: profile.profile.phone ?? "",
    location: profile.profile.location ?? "",
    college: profile.profile.college ?? "",
    degree: profile.profile.degree ?? "",
    branch: profile.profile.branch ?? "",
    graduation_year: profile.profile.graduation_year ?? CURRENT_YEAR + 1,
    current_academic_year: profile.profile.current_academic_year ?? "3rd Year",
    cgpa: profile.profile.cgpa ?? "",
    cgpa_scale: profile.profile.cgpa_scale ?? 10,
    headline: profile.profile.headline ?? "",
    bio: profile.profile.bio ?? "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const set = (key: keyof typeof form) => (value: any) =>
    setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const next: Record<string, string> = {};
    if (form.full_name.trim().length < 2) next.full_name = "Required";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) next.email = "Enter a valid email";
    if (form.college.trim().length < 2) next.college = "Required";
    if (form.degree.trim().length < 2) next.degree = "Required";
    if (!form.branch.trim()) next.branch = "Required";
    if (form.cgpa !== "" && Number(form.cgpa) > Number(form.cgpa_scale))
      next.cgpa = `Cannot exceed your scale of ${form.cgpa_scale}`;
    setErrors(next);
    if (Object.keys(next).length) return;

    await onSubmit({
      ...form,
      phone: form.phone || null,
      location: form.location || null,
      headline: form.headline || null,
      bio: form.bio || null,
      graduation_year: Number(form.graduation_year),
      cgpa: form.cgpa === "" ? null : Number(form.cgpa),
      cgpa_scale: Number(form.cgpa_scale),
    });
  };

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <TextInput
          label="Full name"
          required
          value={form.full_name}
          onChange={(event) => set("full_name")(event.target.value)}
          error={errors.full_name}
        />
        <TextInput
          label="Email"
          required
          type="email"
          value={form.email}
          onChange={(event) => set("email")(event.target.value)}
          error={errors.email}
        />
        <TextInput
          label="Phone number"
          value={form.phone}
          placeholder="+91 98765 43210"
          onChange={(event) => set("phone")(event.target.value)}
          error={errors.phone}
        />
        <TextInput
          label="Location"
          value={form.location}
          placeholder="City, State"
          onChange={(event) => set("location")(event.target.value)}
        />
      </div>

      <div className="border-t border-line pt-5">
        <p className="section-label mb-3">Current academics</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextInput
            label="College / University"
            required
            className="sm:col-span-2"
            value={form.college}
            onChange={(event) => set("college")(event.target.value)}
            error={errors.college}
          />
          <TextInput
            label="Degree"
            required
            placeholder="B.Tech, BBA, MBA, M.Com"
            value={form.degree}
            onChange={(event) => set("degree")(event.target.value)}
            error={errors.degree}
          />
          <TextInput
            label="Branch / Specialisation"
            required
            placeholder="Computer Science, Finance"
            value={form.branch}
            onChange={(event) => set("branch")(event.target.value)}
            error={errors.branch}
          />
          <TextInput
            label="Graduation year"
            required
            type="number"
            min={1990}
            max={CURRENT_YEAR + 10}
            value={form.graduation_year}
            onChange={(event) => set("graduation_year")(event.target.value)}
          />
          <Select
            label="Current academic year"
            required
            value={form.current_academic_year}
            onChange={(event) => set("current_academic_year")(event.target.value)}
            options={ACADEMIC_YEARS.map((year) => ({ value: year, label: year }))}
          />
          <TextInput
            label="CGPA"
            type="number"
            step="0.01"
            min={0}
            value={form.cgpa}
            placeholder="8.4"
            hint="Optional, but several rubrics screen on it."
            onChange={(event) => set("cgpa")(event.target.value)}
            error={errors.cgpa}
          />
          <Select
            label="CGPA scale"
            value={String(form.cgpa_scale)}
            onChange={(event) => set("cgpa_scale")(event.target.value)}
            options={[
              { value: "10", label: "Out of 10" },
              { value: "4", label: "Out of 4" },
              { value: "100", label: "Percentage (out of 100)" },
            ]}
          />
        </div>
      </div>

      <div className="border-t border-line pt-5">
        <p className="section-label mb-3">About you</p>
        <div className="space-y-4">
          <TextInput
            label="Headline"
            value={form.headline}
            placeholder="Backend-leaning CSE undergrad who likes systems work"
            onChange={(event) => set("headline")(event.target.value)}
          />
          <TextArea
            label="Short bio"
            value={form.bio}
            rows={3}
            placeholder="Two or three lines on what you are working on and what you want next."
            onChange={(event) => set("bio")(event.target.value)}
          />
        </div>
      </div>

      <StepActions saving={saving} />
    </form>
  );
}

// ---------------------------------------------------------------------------
// Step 2 - academics
// ---------------------------------------------------------------------------
type AcademicDraft = Omit<AcademicEntry, "id"> & { id: number | null };

const emptyAcademic = (): AcademicDraft => ({
  id: null,
  level: "undergraduate",
  institution: "",
  board_or_university: "",
  degree_or_program: "",
  specialization: "",
  score: null,
  score_type: "cgpa",
  start_year: null,
  end_year: null,
  is_current: false,
  achievements: "",
  relevant_coursework: [],
});

function AcademicsStep({
  profile,
  saving,
  onSubmit,
}: StepProps & { onSubmit: (body: unknown) => Promise<boolean> }) {
  const [entries, setEntries] = useState<AcademicDraft[]>(() =>
    profile.academics.length
      ? profile.academics.map((item) => ({ ...item, id: item.id }))
      : [
          {
            ...emptyAcademic(),
            institution: profile.profile.college ?? "",
            degree_or_program: profile.profile.degree ?? "",
            specialization: profile.profile.branch ?? "",
            score: profile.profile.cgpa,
            is_current: true,
            end_year: profile.profile.graduation_year,
          },
        ]
  );
  const [error, setError] = useState<string | null>(null);

  const update = (index: number, patch: Partial<AcademicDraft>) =>
    setEntries((current) =>
      current.map((entry, position) => (position === index ? { ...entry, ...patch } : entry))
    );

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!entries.length) {
      setError("Add at least one education entry.");
      return;
    }
    if (entries.some((entry) => entry.institution.trim().length < 2)) {
      setError("Every entry needs an institution name.");
      return;
    }
    setError(null);
    await onSubmit({
      entries: entries.map((entry) => ({
        ...entry,
        id: entry.id ?? undefined,
        score: entry.score === null || entry.score === ("" as any) ? null : Number(entry.score),
        start_year: entry.start_year ? Number(entry.start_year) : null,
        end_year: entry.end_year ? Number(entry.end_year) : null,
        board_or_university: entry.board_or_university || null,
        degree_or_program: entry.degree_or_program || null,
        specialization: entry.specialization || null,
        achievements: entry.achievements || null,
      })),
    });
  };

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      {error ? <ErrorState message={error} /> : null}

      <div className="space-y-4">
        {entries.map((entry, index) => (
          <RepeaterItem
            key={index}
            index={index}
            title={ACADEMIC_LEVEL_LABELS[entry.level] ?? "Education"}
            removable={entries.length > 1}
            onRemove={() =>
              setEntries((current) => current.filter((_, position) => position !== index))
            }
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Level"
                required
                value={entry.level}
                onChange={(event) => update(index, { level: event.target.value })}
                options={Object.entries(ACADEMIC_LEVEL_LABELS).map(([value, label]) => ({
                  value,
                  label,
                }))}
              />
              <TextInput
                label="Institution"
                required
                value={entry.institution}
                onChange={(event) => update(index, { institution: event.target.value })}
              />
              <TextInput
                label="Board / University"
                value={entry.board_or_university ?? ""}
                onChange={(event) => update(index, { board_or_university: event.target.value })}
              />
              <TextInput
                label="Degree / Programme"
                value={entry.degree_or_program ?? ""}
                onChange={(event) => update(index, { degree_or_program: event.target.value })}
              />
              <TextInput
                label="Specialisation"
                value={entry.specialization ?? ""}
                onChange={(event) => update(index, { specialization: event.target.value })}
              />
              <div className="grid grid-cols-2 gap-3">
                <TextInput
                  label="Score"
                  type="number"
                  step="0.01"
                  value={entry.score ?? ""}
                  onChange={(event) =>
                    update(index, {
                      score: event.target.value === "" ? null : Number(event.target.value),
                    })
                  }
                />
                <Select
                  label="Type"
                  value={entry.score_type ?? "cgpa"}
                  onChange={(event) => update(index, { score_type: event.target.value })}
                  options={[
                    { value: "cgpa", label: "CGPA" },
                    { value: "percentage", label: "Percentage" },
                  ]}
                />
              </div>
              <TextInput
                label="Start year"
                type="number"
                value={entry.start_year ?? ""}
                onChange={(event) =>
                  update(index, {
                    start_year: event.target.value === "" ? null : Number(event.target.value),
                  })
                }
              />
              <TextInput
                label="End year"
                type="number"
                value={entry.end_year ?? ""}
                onChange={(event) =>
                  update(index, {
                    end_year: event.target.value === "" ? null : Number(event.target.value),
                  })
                }
              />
            </div>

            <Checkbox
              checked={entry.is_current}
              onChange={(next) => update(index, { is_current: next })}
              label="This is my current programme"
            />

            <TagInput
              label="Relevant coursework"
              hint="Counts towards domain knowledge for technical and finance roles."
              values={entry.relevant_coursework}
              onChange={(next) => update(index, { relevant_coursework: next })}
              placeholder="Data Structures, Corporate Finance..."
            />

            <TextArea
              label="Academic achievements"
              value={entry.achievements ?? ""}
              rows={2}
              placeholder="Department rank, scholarships, merit awards..."
              onChange={(event) => update(index, { achievements: event.target.value })}
            />
          </RepeaterItem>
        ))}
      </div>

      <Button
        type="button"
        variant="outline"
        icon={<Plus size={15} />}
        onClick={() => setEntries((current) => [...current, emptyAcademic()])}
      >
        Add another qualification
      </Button>

      <StepActions saving={saving} />
    </form>
  );
}

// ---------------------------------------------------------------------------
// Step 3 - skills
// ---------------------------------------------------------------------------
type SkillDraft = {
  skill_id: number | null;
  name: string;
  category: string | null;
  proficiency: "beginner" | "intermediate" | "advanced";
};

function SkillsStep({
  profile,
  skillOptions,
  saving,
  onSubmit,
}: StepProps & { onSubmit: (body: unknown) => Promise<boolean> }) {
  const [skills, setSkills] = useState<SkillDraft[]>(() =>
    profile.skills.map((item) => ({
      skill_id: item.skill_id,
      name: item.name,
      category: item.category,
      proficiency: item.proficiency,
    }))
  );
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  const chosen = new Set(skills.map((item) => item.name.toLowerCase()));

  const suggestions = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return skillOptions
      .filter((option) => !chosen.has(option.name.toLowerCase()))
      .filter((option) => (needle ? option.name.toLowerCase().includes(needle) : true))
      .slice(0, needle ? 10 : 0);
  }, [query, skillOptions, skills]);

  const grouped = useMemo(() => {
    const popular = skillOptions.filter((option) => !option.is_custom);
    const buckets: Record<string, SkillOption[]> = {};
    for (const option of popular) {
      buckets[option.category] = buckets[option.category] ?? [];
      if (buckets[option.category].length < 10) buckets[option.category].push(option);
    }
    return buckets;
  }, [skillOptions]);

  const add = (name: string, skillId: number | null, category: string | null) => {
    const clean = name.trim();
    if (!clean || chosen.has(clean.toLowerCase())) return;
    setSkills((current) => [
      ...current,
      { skill_id: skillId, name: clean, category, proficiency: "intermediate" },
    ]);
    setQuery("");
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!skills.length) {
      setError("Add at least one skill.");
      return;
    }
    setError(null);
    await onSubmit({
      skills: skills.map((item) => ({
        skill_id: item.skill_id ?? undefined,
        name: item.name,
        category: item.category ?? undefined,
        proficiency: item.proficiency,
      })),
    });
  };

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      {error ? <ErrorState message={error} /> : null}

      <InlineNote tone="brand" icon={<Zap size={15} />}>
        Add any skill, even if it is not in our list. Proficiency is your own assessment - we score
        it against evidence from your projects and internships separately.
      </InlineNote>

      <Field label="Search or type a skill" hint="Press Enter to add a skill of your own.">
        <div className="relative">
          <TextInput
            value={query}
            placeholder="Python, Financial Modelling, Power BI..."
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                const exact = skillOptions.find(
                  (option) => option.name.toLowerCase() === query.trim().toLowerCase()
                );
                add(query, exact?.id ?? null, exact?.category ?? null);
              }
            }}
          />
          {suggestions.length ? (
            <div className="absolute z-20 mt-1 max-h-60 w-full overflow-y-auto rounded-xl border border-line bg-white shadow-float animate-fade-in">
              {suggestions.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => add(option.name, option.id, option.category)}
                  className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-brand-50"
                >
                  <span className="flex items-center gap-2 text-ink-800">
                    <Plus size={13} className="text-brand-500" />
                    {option.name}
                  </span>
                  <span className="text-2xs text-ink-400">
                    {SKILL_CATEGORY_LABELS[option.category] ?? option.category}
                  </span>
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </Field>

      {/* Selected skills with proficiency */}
      {skills.length ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="section-label">Your skills ({skills.length})</p>
            <button
              type="button"
              onClick={() => setSkills([])}
              className="text-xs font-semibold text-danger-700 hover:underline"
            >
              Clear all
            </button>
          </div>
          <div className="divide-y divide-line overflow-hidden rounded-2xl border border-line">
            {skills.map((skill, index) => (
              <div
                key={`${skill.name}-${index}`}
                className="flex flex-wrap items-center gap-3 bg-white px-3.5 py-2.5 animate-fade-in"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-ink-900">{skill.name}</p>
                  <p className="text-2xs text-ink-400">
                    {skill.category
                      ? SKILL_CATEGORY_LABELS[skill.category] ?? titleCase(skill.category)
                      : "Custom skill"}
                  </p>
                </div>
                <div className="flex rounded-lg bg-sage-100 p-0.5">
                  {PROFICIENCIES.map((level) => (
                    <button
                      key={level}
                      type="button"
                      onClick={() =>
                        setSkills((current) =>
                          current.map((item, position) =>
                            position === index ? { ...item, proficiency: level } : item
                          )
                        )
                      }
                      className={cn(
                        "rounded-md px-2.5 py-1 text-2xs font-semibold capitalize transition-all",
                        skill.proficiency === level
                          ? "bg-white text-forest-800 shadow-sm"
                          : "text-ink-500 hover:text-forest-700"
                      )}
                    >
                      {level}
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setSkills((current) => current.filter((_, position) => position !== index))
                  }
                  className="rounded-lg px-2 py-1 text-xs font-semibold text-danger-700 transition-colors hover:bg-danger-50"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState
          icon={<Zap size={18} />}
          title="No skills added yet"
          description="Search above, or pick from the suggestions below."
        />
      )}

      {/* Suggested catalogue */}
      <div className="space-y-3 border-t border-line pt-5">
        <p className="section-label">Common skills by category</p>
        {Object.entries(grouped).map(([category, options]) => (
          <div key={category}>
            <p className="mb-1.5 text-xs font-semibold text-ink-600">
              {SKILL_CATEGORY_LABELS[category] ?? titleCase(category)}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {options
                .filter((option) => !chosen.has(option.name.toLowerCase()))
                .map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => add(option.name, option.id, option.category)}
                    className="rounded-lg border border-line bg-white px-2.5 py-1 text-xs font-medium text-ink-600 transition-all hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                  >
                    + {option.name}
                  </button>
                ))}
            </div>
          </div>
        ))}
      </div>

      <StepActions saving={saving} />
    </form>
  );
}

// ---------------------------------------------------------------------------
// Step 4 - projects
// ---------------------------------------------------------------------------
type ProjectDraft = {
  id: number | null;
  title: string;
  description: string;
  contribution: string;
  category: string;
  duration_months: string;
  team_size: string;
  github_url: string;
  live_url: string;
  technologies: string[];
};

const emptyProject = (): ProjectDraft => ({
  id: null,
  title: "",
  description: "",
  contribution: "",
  category: "Web Development",
  duration_months: "",
  team_size: "",
  github_url: "",
  live_url: "",
  technologies: [],
});

function ProjectsStep({
  profile,
  skillOptions,
  saving,
  onSubmit,
}: StepProps & { onSubmit: (body: unknown) => Promise<boolean> }) {
  const [projects, setProjects] = useState<ProjectDraft[]>(() =>
    profile.projects.length
      ? profile.projects.map((item) => ({
          id: item.id,
          title: item.title,
          description: item.description ?? "",
          contribution: item.contribution ?? "",
          category: item.category ?? "Other",
          duration_months: item.duration_months ? String(item.duration_months) : "",
          team_size: item.team_size ? String(item.team_size) : "",
          github_url: item.github_url ?? "",
          live_url: item.live_url ?? "",
          technologies: item.technologies,
        }))
      : [emptyProject()]
  );
  const [error, setError] = useState<string | null>(null);

  const update = (index: number, patch: Partial<ProjectDraft>) =>
    setProjects((current) =>
      current.map((entry, position) => (position === index ? { ...entry, ...patch } : entry))
    );

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const filled = projects.filter((item) => item.title.trim().length > 1);
    if (!filled.length) {
      setError("Add at least one project with a title.");
      return;
    }
    setError(null);
    await onSubmit({
      projects: filled.map((item) => ({
        id: item.id ?? undefined,
        title: item.title,
        description: item.description || null,
        contribution: item.contribution || null,
        category: item.category || null,
        duration_months: item.duration_months ? Number(item.duration_months) : null,
        team_size: item.team_size ? Number(item.team_size) : null,
        github_url: item.github_url || null,
        live_url: item.live_url || null,
        technologies: item.technologies,
      })),
    });
  };

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      {error ? <ErrorState message={error} /> : null}

      <InlineNote tone="brand" icon={<FolderGit2 size={15} />}>
        Describe outcomes, not just features. A quantified result ("cut query time from 6s to
        400ms") reads far better than "worked on performance", and the technologies you list here
        are what convert your skill claims into evidence.
      </InlineNote>

      <div className="space-y-4">
        {projects.map((project, index) => (
          <RepeaterItem
            key={index}
            index={index}
            title={project.title.trim() || "New project"}
            removable={projects.length > 1}
            onRemove={() =>
              setProjects((current) => current.filter((_, position) => position !== index))
            }
          >
            <TextInput
              label="Project title"
              required
              value={project.title}
              onChange={(event) => update(index, { title: event.target.value })}
            />

            <TextArea
              label="Description"
              rows={3}
              value={project.description}
              placeholder="What problem it solved, how it worked, and the result."
              onChange={(event) => update(index, { description: event.target.value })}
            />

            <TextArea
              label="Your individual contribution"
              rows={2}
              value={project.contribution}
              placeholder="What you personally built or owned, and the team size."
              onChange={(event) => update(index, { contribution: event.target.value })}
            />

            <TagInput
              label="Technologies / skills used"
              hint="Matched against each role's required skills."
              values={project.technologies}
              suggestions={skillOptions.map((option) => option.name)}
              onChange={(next) => update(index, { technologies: next })}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Category"
                value={project.category}
                onChange={(event) => update(index, { category: event.target.value })}
                options={PROJECT_CATEGORIES.map((value) => ({ value, label: value }))}
              />
              <div className="grid grid-cols-2 gap-3">
                <TextInput
                  label="Duration (months)"
                  type="number"
                  min={0}
                  value={project.duration_months}
                  onChange={(event) => update(index, { duration_months: event.target.value })}
                />
                <TextInput
                  label="Team size"
                  type="number"
                  min={1}
                  value={project.team_size}
                  onChange={(event) => update(index, { team_size: event.target.value })}
                />
              </div>
              <TextInput
                label="GitHub link"
                icon={<Link2 size={14} />}
                value={project.github_url}
                placeholder="github.com/you/project"
                onChange={(event) => update(index, { github_url: event.target.value })}
              />
              <TextInput
                label="Live link"
                icon={<Link2 size={14} />}
                value={project.live_url}
                placeholder="your-project.app"
                onChange={(event) => update(index, { live_url: event.target.value })}
              />
            </div>
          </RepeaterItem>
        ))}
      </div>

      <Button
        type="button"
        variant="outline"
        icon={<Plus size={15} />}
        onClick={() => setProjects((current) => [...current, emptyProject()])}
      >
        Add another project
      </Button>

      <StepActions saving={saving} />
    </form>
  );
}

// ---------------------------------------------------------------------------
// Step 5 - experience, certifications, achievements
// ---------------------------------------------------------------------------
function ExperienceStep({
  profile,
  skillOptions,
  saving,
  onSubmit,
}: StepProps & { onSubmit: (body: unknown) => Promise<boolean> }) {
  const [experiences, setExperiences] = useState(() =>
    profile.experiences.map((item) => ({
      id: item.id as number | null,
      experience_type: item.experience_type,
      organization: item.organization,
      title: item.title,
      description: item.description ?? "",
      location: item.location ?? "",
      duration_months: item.duration_months ? String(item.duration_months) : "",
      is_current: item.is_current,
      skills_used: item.skills_used,
    }))
  );
  const [certifications, setCertifications] = useState(() =>
    profile.certifications.map((item) => ({
      id: item.id as number | null,
      name: item.name,
      issuer: item.issuer ?? "",
      credential_url: item.credential_url ?? "",
      related_skills: item.related_skills,
    }))
  );
  const [achievements, setAchievements] = useState(() =>
    profile.achievements.map((item) => ({
      id: item.id as number | null,
      title: item.title,
      description: item.description ?? "",
      category: item.category,
      scope: item.scope ?? "",
    }))
  );
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const validExperiences = experiences.filter(
      (item) => item.organization.trim() && item.title.trim()
    );
    const validCertifications = certifications.filter((item) => item.name.trim().length > 1);
    const validAchievements = achievements.filter((item) => item.title.trim().length > 1);

    if (!validExperiences.length && !validCertifications.length && !validAchievements.length) {
      setError("Add at least one internship, certification or achievement.");
      return;
    }
    setError(null);

    await onSubmit({
      experiences: validExperiences.map((item) => ({
        id: item.id ?? undefined,
        experience_type: item.experience_type,
        organization: item.organization,
        title: item.title,
        description: item.description || null,
        location: item.location || null,
        duration_months: item.duration_months ? Number(item.duration_months) : null,
        is_current: item.is_current,
        skills_used: item.skills_used,
      })),
      certifications: validCertifications.map((item) => ({
        id: item.id ?? undefined,
        name: item.name,
        issuer: item.issuer || null,
        credential_url: item.credential_url || null,
        related_skills: item.related_skills,
      })),
      achievements: validAchievements.map((item) => ({
        id: item.id ?? undefined,
        title: item.title,
        description: item.description || null,
        category: item.category,
        scope: item.scope || null,
      })),
    });
  };

  return (
    <form onSubmit={submit} className="space-y-7" noValidate>
      {error ? <ErrorState message={error} /> : null}

      {/* Experience */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Briefcase size={16} className="text-brand-600" />
          <h3 className="text-sm font-bold">Internships, work & responsibilities</h3>
        </div>

        {experiences.length ? (
          experiences.map((item, index) => (
            <RepeaterItem
              key={index}
              index={index}
              title={
                item.title.trim()
                  ? `${item.title}${item.organization ? ` · ${item.organization}` : ""}`
                  : "New entry"
              }
              onRemove={() =>
                setExperiences((current) => current.filter((_, position) => position !== index))
              }
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <Select
                  label="Type"
                  required
                  value={item.experience_type}
                  onChange={(event) =>
                    setExperiences((current) =>
                      current.map((entry, position) =>
                        position === index
                          ? { ...entry, experience_type: event.target.value }
                          : entry
                      )
                    )
                  }
                  options={Object.entries(EXPERIENCE_TYPE_LABELS).map(([value, label]) => ({
                    value,
                    label,
                  }))}
                />
                <TextInput
                  label="Organisation"
                  required
                  value={item.organization}
                  onChange={(event) =>
                    setExperiences((current) =>
                      current.map((entry, position) =>
                        position === index ? { ...entry, organization: event.target.value } : entry
                      )
                    )
                  }
                />
                <TextInput
                  label="Role title"
                  required
                  value={item.title}
                  onChange={(event) =>
                    setExperiences((current) =>
                      current.map((entry, position) =>
                        position === index ? { ...entry, title: event.target.value } : entry
                      )
                    )
                  }
                />
                <TextInput
                  label="Duration (months)"
                  type="number"
                  min={0}
                  value={item.duration_months}
                  onChange={(event) =>
                    setExperiences((current) =>
                      current.map((entry, position) =>
                        position === index
                          ? { ...entry, duration_months: event.target.value }
                          : entry
                      )
                    )
                  }
                />
              </div>

              <TextArea
                label="What you did"
                rows={2}
                value={item.description}
                placeholder="Outcomes, not duties. Numbers where you have them."
                onChange={(event) =>
                  setExperiences((current) =>
                    current.map((entry, position) =>
                      position === index ? { ...entry, description: event.target.value } : entry
                    )
                  )
                }
              />

              <TagInput
                label="Skills used"
                values={item.skills_used}
                suggestions={skillOptions.map((option) => option.name)}
                onChange={(next) =>
                  setExperiences((current) =>
                    current.map((entry, position) =>
                      position === index ? { ...entry, skills_used: next } : entry
                    )
                  )
                }
              />
            </RepeaterItem>
          ))
        ) : (
          <EmptyState
            icon={<Briefcase size={18} />}
            title="No experience added"
            description="Internships and positions of responsibility both count here."
          />
        )}

        <Button
          type="button"
          variant="outline"
          size="sm"
          icon={<Plus size={14} />}
          onClick={() =>
            setExperiences((current) => [
              ...current,
              {
                id: null,
                experience_type: "internship",
                organization: "",
                title: "",
                description: "",
                location: "",
                duration_months: "",
                is_current: false,
                skills_used: [],
              },
            ])
          }
        >
          Add experience
        </Button>
      </section>

      {/* Certifications */}
      <section className="space-y-4 border-t border-line pt-6">
        <div className="flex items-center gap-2">
          <Award size={16} className="text-brand-600" />
          <h3 className="text-sm font-bold">Certifications</h3>
        </div>

        {certifications.map((item, index) => (
          <RepeaterItem
            key={index}
            index={index}
            title={item.name.trim() || "New certification"}
            onRemove={() =>
              setCertifications((current) => current.filter((_, position) => position !== index))
            }
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <TextInput
                label="Certification name"
                required
                value={item.name}
                onChange={(event) =>
                  setCertifications((current) =>
                    current.map((entry, position) =>
                      position === index ? { ...entry, name: event.target.value } : entry
                    )
                  )
                }
              />
              <TextInput
                label="Issuer"
                value={item.issuer}
                onChange={(event) =>
                  setCertifications((current) =>
                    current.map((entry, position) =>
                      position === index ? { ...entry, issuer: event.target.value } : entry
                    )
                  )
                }
              />
              <TextInput
                label="Credential URL"
                className="sm:col-span-2"
                icon={<Link2 size={14} />}
                value={item.credential_url}
                onChange={(event) =>
                  setCertifications((current) =>
                    current.map((entry, position) =>
                      position === index ? { ...entry, credential_url: event.target.value } : entry
                    )
                  )
                }
              />
            </div>
            <TagInput
              label="Related skills"
              values={item.related_skills}
              suggestions={skillOptions.map((option) => option.name)}
              onChange={(next) =>
                setCertifications((current) =>
                  current.map((entry, position) =>
                    position === index ? { ...entry, related_skills: next } : entry
                  )
                )
              }
            />
          </RepeaterItem>
        ))}

        <Button
          type="button"
          variant="outline"
          size="sm"
          icon={<Plus size={14} />}
          onClick={() =>
            setCertifications((current) => [
              ...current,
              { id: null, name: "", issuer: "", credential_url: "", related_skills: [] },
            ])
          }
        >
          Add certification
        </Button>
      </section>

      {/* Achievements */}
      <section className="space-y-4 border-t border-line pt-6">
        <div className="flex items-center gap-2">
          <Award size={16} className="text-brand-600" />
          <h3 className="text-sm font-bold">Achievements, competitions & extracurriculars</h3>
        </div>

        {achievements.map((item, index) => (
          <RepeaterItem
            key={index}
            index={index}
            title={item.title.trim() || "New achievement"}
            onRemove={() =>
              setAchievements((current) => current.filter((_, position) => position !== index))
            }
          >
            <TextInput
              label="Title"
              required
              value={item.title}
              onChange={(event) =>
                setAchievements((current) =>
                  current.map((entry, position) =>
                    position === index ? { ...entry, title: event.target.value } : entry
                  )
                )
              }
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Category"
                value={item.category}
                onChange={(event) =>
                  setAchievements((current) =>
                    current.map((entry, position) =>
                      position === index ? { ...entry, category: event.target.value } : entry
                    )
                  )
                }
                options={[
                  { value: "competition", label: "Competition" },
                  { value: "academic", label: "Academic" },
                  { value: "extracurricular", label: "Extracurricular" },
                  { value: "other", label: "Other" },
                ]}
              />
              <TextInput
                label="Scope"
                value={item.scope}
                placeholder="college / regional / national"
                onChange={(event) =>
                  setAchievements((current) =>
                    current.map((entry, position) =>
                      position === index ? { ...entry, scope: event.target.value } : entry
                    )
                  )
                }
              />
            </div>
          </RepeaterItem>
        ))}

        <Button
          type="button"
          variant="outline"
          size="sm"
          icon={<Plus size={14} />}
          onClick={() =>
            setAchievements((current) => [
              ...current,
              { id: null, title: "", description: "", category: "competition", scope: "" },
            ])
          }
        >
          Add achievement
        </Button>
      </section>

      <StepActions saving={saving} />
    </form>
  );
}

// ---------------------------------------------------------------------------
// Step 6 - resume
// ---------------------------------------------------------------------------
function ResumeStep({ profile, onSaved, goTo }: StepProps) {
  const { push } = useToast();
  const [review, setReview] = useState<ResumeReview | null>(null);
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [selection, setSelection] = useState<{
    import_contact: boolean;
    skills: string[];
    projects: string[];
    experience: string[];
    certifications: string[];
    achievements: string[];
  }>({
    import_contact: true,
    skills: [],
    projects: [],
    experience: [],
    certifications: [],
    achievements: [],
  });

  // Load any previously uploaded resume so the step is resumable.
  useEffect(() => {
    if (!profile.resume) return;
    api
      .resumeReview()
      .then(setReview)
      .catch(() => setReview(null));
  }, [profile.resume]);

  // Pre-tick everything that is genuinely new.
  useEffect(() => {
    const suggestions = review?.suggestions;
    if (!suggestions) return;
    setSelection({
      import_contact: true,
      skills: suggestions.skills.filter((item) => !item.already_in_profile).map((item) => item.name),
      projects: suggestions.projects
        .filter((item) => !item.already_in_profile)
        .map((item) => item.title),
      experience: suggestions.experience
        .filter((item) => !item.already_in_profile)
        .map((item) => `${item.title}|${item.organization}`),
      certifications: suggestions.certifications
        .filter((item) => !item.already_in_profile)
        .map((item) => item.name),
      achievements: suggestions.achievements
        .filter((item) => !item.already_in_profile)
        .map((item) => item.title),
    });
  }, [review]);

  const upload = async (file: File) => {
    const extension = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
    if (![".pdf", ".docx"].includes(extension)) {
      push({ title: "Unsupported file", description: "Upload a PDF or DOCX.", variant: "error" });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      push({ title: "File too large", description: "Maximum size is 5 MB.", variant: "error" });
      return;
    }
    setUploading(true);
    try {
      const result = await api.uploadResume(file);
      setReview(result.review);
      await onSaved(result.message, result.recalculated_roles);
    } catch (error) {
      push({
        title: "Upload failed",
        description: error instanceof ApiError ? error.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setUploading(false);
    }
  };

  const runImport = async () => {
    setImporting(true);
    try {
      const result = await api.importResume(selection);
      await onSaved(result.message, result.recalculated_roles);
      const fresh = await api.resumeReview();
      setReview(fresh);
    } catch (error) {
      push({
        title: "Import failed",
        description: error instanceof ApiError ? error.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setImporting(false);
    }
  };

  const toggle = (bucket: keyof typeof selection, value: string) =>
    setSelection((current) => {
      const list = current[bucket] as string[];
      return {
        ...current,
        [bucket]: list.includes(value)
          ? list.filter((item) => item !== value)
          : [...list, value],
      };
    });

  const quality = review?.quality;

  return (
    <div className="space-y-5">
      <InlineNote tone="info" icon={<FileText size={15} />}>
        Your resume is analysed alongside what you typed, never instead of it. Review the extracted
        items below and tick only what you want imported - existing entries are left untouched and
        blank profile fields are the only ones filled automatically.
      </InlineNote>

      {/* Dropzone */}
      <label
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files?.[0];
          if (file) upload(file);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-all duration-200",
          dragging
            ? "border-brand-500 bg-brand-50"
            : "border-line-strong bg-surface-muted hover:border-brand-300 hover:bg-brand-50/30"
        )}
      >
        <input
          type="file"
          accept=".pdf,.docx"
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) upload(file);
            event.target.value = "";
          }}
        />
        <span className="grid h-12 w-12 place-items-center rounded-2xl bg-forest-800 text-white">
          {uploading ? <Loader2 size={20} className="animate-spin" /> : <Upload size={20} />}
        </span>
        <p className="mt-3 text-sm font-semibold text-ink-800">
          {uploading ? "Analysing your resume..." : "Drop your resume here, or click to browse"}
        </p>
        <p className="mt-1 text-xs text-ink-500">PDF or DOCX, up to 5 MB</p>
        {profile.resume ? (
          <p className="mt-3 text-xs text-brand-700">
            Current file: <strong>{profile.resume.original_filename}</strong>
            {profile.resume.quality_score !== null
              ? ` · quality ${profile.resume.quality_score}/100`
              : ""}
          </p>
        ) : null}
      </label>

      {review?.parse_status === "failed" ? (
        <ErrorState
          message={
            review.parse_error ??
            "We could not read any text from that file. If it is a scanned PDF, upload a text-based version."
          }
        />
      ) : null}

      {/* Quality report */}
      {quality ? (
        <Card className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
            <div>
              <p className="section-label">Resume quality</p>
              <p className="font-display text-2xl font-extrabold text-forest-800">
                {quality.score}
                <span className="text-sm font-semibold text-ink-400">/100</span>
              </p>
            </div>
            <div className="text-right text-xs text-ink-500">
              <p>{quality.word_count} words</p>
              <p>{quality.sections_found.length} sections detected</p>
            </div>
          </div>

          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {quality.checks.map((check) => (
              <div
                key={check.key}
                className={cn(
                  "rounded-xl border px-3 py-2.5",
                  check.passed
                    ? "border-brand-100 bg-brand-50/50"
                    : "border-warn-500/20 bg-warn-50/50"
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold text-ink-800">{check.label}</p>
                  <span className="shrink-0 text-2xs font-bold tabular-nums text-ink-500">
                    {check.earned}/{check.possible}
                  </span>
                </div>
                <p className="mt-0.5 text-2xs leading-relaxed text-ink-500">{check.detail}</p>
              </div>
            ))}
          </div>

          {quality.improvements.length ? (
            <div className="mt-4 border-t border-line pt-4">
              <p className="section-label mb-2">Suggested improvements</p>
              <ul className="space-y-1.5">
                {quality.improvements.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-xs text-ink-600">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-warn-500" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </Card>
      ) : null}

      {/* Review and import */}
      {review?.suggestions ? (
        <Card className="p-5">
          <div className="mb-4 border-b border-line pb-4">
            <h3 className="text-sm font-bold">What we found - choose what to import</h3>
            <p className="mt-0.5 text-xs text-ink-500">{review.notice}</p>
          </div>

          <div className="space-y-5">
            <ReviewGroup
              title="Skills"
              items={review.suggestions.skills.map((item) => ({
                key: item.name,
                label: item.name,
                meta: item.already_in_profile ? "already in profile" : undefined,
                disabled: item.already_in_profile,
              }))}
              selected={selection.skills}
              onToggle={(value) => toggle("skills", value)}
            />
            <ReviewGroup
              title="Projects"
              items={review.suggestions.projects.map((item) => ({
                key: item.title,
                label: item.title,
                meta: item.already_in_profile
                  ? "already in profile"
                  : item.technologies?.length
                    ? item.technologies.slice(0, 4).join(", ")
                    : undefined,
                disabled: item.already_in_profile,
              }))}
              selected={selection.projects}
              onToggle={(value) => toggle("projects", value)}
            />
            <ReviewGroup
              title="Experience"
              items={review.suggestions.experience.map((item) => ({
                key: `${item.title}|${item.organization}`,
                label: `${item.title} · ${item.organization}`,
                meta: item.already_in_profile
                  ? "already in profile"
                  : EXPERIENCE_TYPE_LABELS[item.experience_type],
                disabled: item.already_in_profile,
              }))}
              selected={selection.experience}
              onToggle={(value) => toggle("experience", value)}
            />
            <ReviewGroup
              title="Certifications"
              items={review.suggestions.certifications.map((item) => ({
                key: item.name,
                label: item.name,
                meta: item.already_in_profile ? "already in profile" : item.issuer ?? undefined,
                disabled: item.already_in_profile,
              }))}
              selected={selection.certifications}
              onToggle={(value) => toggle("certifications", value)}
            />
            <ReviewGroup
              title="Achievements"
              items={review.suggestions.achievements.map((item) => ({
                key: item.title,
                label: item.title,
                meta: item.already_in_profile ? "already in profile" : titleCase(item.category),
                disabled: item.already_in_profile,
              }))}
              selected={selection.achievements}
              onToggle={(value) => toggle("achievements", value)}
            />

            <div className="border-t border-line pt-4">
              <Checkbox
                checked={selection.import_contact}
                onChange={(next) => setSelection((current) => ({ ...current, import_contact: next }))}
                label="Fill blank contact fields"
                description="Phone, GitHub and LinkedIn are filled only where your profile is currently empty."
              />
            </div>
          </div>

          <div className="mt-5 flex flex-wrap justify-end gap-2 border-t border-line pt-4">
            <Button variant="ghost" onClick={() => goTo(7)}>
              Skip importing
            </Button>
            <Button loading={importing} onClick={runImport} icon={<CheckCircle2 size={16} />}>
              Import selected
            </Button>
          </div>
        </Card>
      ) : null}

      <div className="flex justify-end border-t border-line pt-5">
        <Button onClick={() => goTo(7)} icon={<ArrowRight size={16} />}>
          Continue to career preferences
        </Button>
      </div>
    </div>
  );
}

function ReviewGroup({
  title,
  items,
  selected,
  onToggle,
}: {
  title: string;
  items: { key: string; label: string; meta?: string; disabled?: boolean }[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  if (!items.length) {
    return (
      <div>
        <p className="section-label mb-2">{title}</p>
        <p className="text-xs text-ink-400">Nothing detected in this section.</p>
      </div>
    );
  }
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="section-label">{title}</p>
        <span className="text-2xs text-ink-400">
          {selected.length} of {items.filter((item) => !item.disabled).length} selected
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => {
          const active = selected.includes(item.key);
          return (
            <button
              key={item.key}
              type="button"
              disabled={item.disabled}
              onClick={() => onToggle(item.key)}
              className={cn(
                "max-w-full rounded-xl border px-2.5 py-1.5 text-left text-xs transition-all duration-200",
                item.disabled
                  ? "cursor-not-allowed border-line bg-sage-50 text-ink-400"
                  : active
                    ? "border-brand-400 bg-brand-50 text-brand-800"
                    : "border-line bg-white text-ink-600 hover:border-brand-200"
              )}
            >
              <span className="flex items-center gap-1.5">
                {!item.disabled ? (
                  <span
                    className={cn(
                      "grid h-3.5 w-3.5 shrink-0 place-items-center rounded border",
                      active ? "border-brand-600 bg-brand-600 text-white" : "border-line-strong"
                    )}
                  >
                    {active ? <CheckCircle2 size={9} /> : null}
                  </span>
                ) : null}
                <span className="truncate font-medium">{item.label}</span>
              </span>
              {item.meta ? (
                <span className="mt-0.5 block truncate text-2xs text-ink-400">{item.meta}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 7 - portfolio + preferences
// ---------------------------------------------------------------------------
function PreferencesStep({
  profile,
  domains,
  saving,
  onSubmit,
}: StepProps & { onSubmit: (body: unknown) => Promise<boolean> }) {
  const [links, setLinks] = useState({
    github_url: profile.profile.github_url ?? "",
    linkedin_url: profile.profile.linkedin_url ?? "",
    portfolio_url: profile.profile.portfolio_url ?? "",
  });
  const [roleIds, setRoleIds] = useState<number[]>(
    profile.preferences.map((item) => item.role_id)
  );
  const [primary, setPrimary] = useState<number | null>(
    profile.preferences.find((item) => item.is_primary)?.role_id ?? null
  );
  const [error, setError] = useState<string | null>(null);

  const toggleRole = (id: number) =>
    setRoleIds((current) => {
      const next = current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id];
      if (!next.includes(primary ?? -1)) setPrimary(next[0] ?? null);
      return next;
    });

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!roleIds.length) {
      setError("Select at least one target role.");
      return;
    }
    setError(null);
    await onSubmit({
      ...links,
      github_url: links.github_url || null,
      linkedin_url: links.linkedin_url || null,
      portfolio_url: links.portfolio_url || null,
      other_links: [],
      role_ids: roleIds,
      primary_role_id: primary ?? roleIds[0],
    });
  };

  return (
    <form onSubmit={submit} className="space-y-6" noValidate>
      {error ? <ErrorState message={error} /> : null}

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Link2 size={16} className="text-brand-600" />
          <h3 className="text-sm font-bold">Portfolio links</h3>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <TextInput
            label="GitHub"
            value={links.github_url}
            placeholder="github.com/you"
            onChange={(event) => setLinks({ ...links, github_url: event.target.value })}
          />
          <TextInput
            label="LinkedIn"
            value={links.linkedin_url}
            placeholder="linkedin.com/in/you"
            onChange={(event) => setLinks({ ...links, linkedin_url: event.target.value })}
          />
          <TextInput
            label="Portfolio / website"
            value={links.portfolio_url}
            placeholder="yoursite.dev"
            onChange={(event) => setLinks({ ...links, portfolio_url: event.target.value })}
          />
        </div>
      </section>

      <section className="space-y-4 border-t border-line pt-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Target size={16} className="text-brand-600" />
            <h3 className="text-sm font-bold">Target roles</h3>
          </div>
          <Badge tone={roleIds.length ? "brand" : "neutral"}>{roleIds.length} selected</Badge>
        </div>

        <InlineNote tone="brand" icon={<BookOpen size={15} />}>
          Pick the roles you actually want. Every active role still gets scored, so you will also
          see matches you did not ask for - but these drive your dashboard and roadmap.
        </InlineNote>

        <div className="space-y-4">
          {domains.map((domain) => (
            <div key={domain.id} className="rounded-2xl border border-line bg-surface-muted p-4">
              <div className="mb-3 flex items-center gap-2.5">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: domain.accent_color ?? "#187C4F" }}
                />
                <p className="text-sm font-bold text-ink-800">{domain.name}</p>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {domain.roles.map((role) => {
                  const selected = roleIds.includes(role.id);
                  return (
                    <div
                      key={role.id}
                      className={cn(
                        "rounded-xl border bg-white p-3 transition-all duration-200",
                        selected ? "border-brand-300 ring-1 ring-brand-200" : "border-line"
                      )}
                    >
                      <Checkbox
                        checked={selected}
                        onChange={() => toggleRole(role.id)}
                        label={role.name}
                        description={role.description ?? undefined}
                      />
                      {selected ? (
                        <button
                          type="button"
                          onClick={() => setPrimary(role.id)}
                          className={cn(
                            "mt-2 w-full rounded-lg px-2 py-1.5 text-2xs font-semibold transition-colors",
                            primary === role.id
                              ? "bg-forest-800 text-white"
                              : "bg-sage-100 text-ink-600 hover:bg-sage-200"
                          )}
                        >
                          {primary === role.id ? "Primary target" : "Make primary"}
                        </button>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </section>

      <StepActions saving={saving} label="Save preferences" />
    </form>
  );
}
