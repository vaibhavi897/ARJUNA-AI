/**
 * Settings / profile management.
 *
 * Section editors reuse the same endpoints onboarding uses, so a change here
 * runs identical validation, triggers the same targeted rescore, and the
 * dashboard reflects it on the next load. No duplicated client-side copies.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Award,
  Briefcase,
  CheckCircle2,
  FileText,
  FolderGit2,
  GraduationCap,
  KeyRound,
  Link2,
  SlidersHorizontal,
  Target,
  UserCircle2,
  Zap,
} from "lucide-react";
import { AppShell } from "../components/layout";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  Field,
  InlineNote,
  PageLoader,
  ProgressBar,
  SectionHeader,
  Tabs,
  TextInput,
  Toggle,
} from "../components/ui";
import {
  ApiError,
  api,
  type CareerDomain,
  type FullProfile,
  type SkillOption,
  type StudentSettings as SettingsPayload,
} from "../lib/api";
import { useAuth, useToast } from "../lib/auth";
import { cn, formatDate, titleCase } from "../lib/utils";

const SECTION_TABS = [
  { id: "profile", label: "Profile" },
  { id: "skills", label: "Skills" },
  { id: "projects", label: "Projects" },
  { id: "experience", label: "Experience" },
  { id: "preferences", label: "Career targets" },
  { id: "account", label: "Account" },
];

export default function Settings() {
  const { user, refreshUser } = useAuth();
  const { push } = useToast();

  const [tab, setTab] = useState("profile");
  const [profile, setProfile] = useState<FullProfile | null>(null);
  const [settings, setSettings] = useState<SettingsPayload | null>(null);
  const [domains, setDomains] = useState<CareerDomain[]>([]);
  const [skillOptions, setSkillOptions] = useState<SkillOption[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [profileData, settingsData] = await Promise.all([api.profile(), api.settings()]);
      setProfile(profileData);
      setSettings(settingsData);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load your settings.");
    }
  }, []);

  useEffect(() => {
    load();
    api.domains().then(setDomains).catch(() => setDomains([]));
    api.skills().then(setSkillOptions).catch(() => setSkillOptions([]));
  }, [load]);

  const notifySaved = async (message: string, recalculated: string[]) => {
    push({
      title: message,
      description: recalculated.length
        ? `${recalculated.length} role score(s) recalculated. Your dashboard is already updated.`
        : "Dashboard updated.",
      variant: "success",
    });
    await load();
    await refreshUser();
  };

  if (error && !profile) {
    return (
      <AppShell title="Settings">
        <ErrorState message={error} onRetry={load} />
      </AppShell>
    );
  }

  if (!profile || !settings) {
    return (
      <AppShell title="Settings">
        <PageLoader label="Loading your profile" />
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Settings & Profile"
      subtitle="Edit any section. Scores and the dashboard update automatically."
      actions={
        <Badge tone={profile.profile.profile_completion === 100 ? "brand" : "neutral"}>
          {profile.profile.profile_completion}% complete
        </Badge>
      }
    >
      <div className="space-y-5">
        <Card className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="section-label">Profile completion</p>
              <div className="mt-1.5 max-w-md">
                <ProgressBar value={profile.profile.profile_completion} showLabel />
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(profile.profile.completion_breakdown).map(([key, value]: any) => (
                <span
                  key={key}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-2xs font-semibold",
                    value.complete
                      ? "border-brand-200 bg-brand-50 text-brand-700"
                      : "border-line bg-white text-ink-400"
                  )}
                >
                  {value.complete ? <CheckCircle2 size={10} /> : null}
                  {value.label}
                </span>
              ))}
            </div>
          </div>
        </Card>

        <Tabs tabs={SECTION_TABS} active={tab} onChange={setTab} />

        {tab === "profile" ? (
          <ProfileSection profile={profile} onSaved={notifySaved} />
        ) : null}
        {tab === "skills" ? (
          <RedirectSection
            icon={<Zap size={18} />}
            title="Skills"
            body="Skills are edited in the onboarding skills step, which has the search, proficiency controls and custom-skill entry."
            count={`${profile.skills.length} skills · ${profile.skills.filter((s) => s.is_evidence_backed).length} evidence-backed`}
            to="/onboarding?step=3"
            items={profile.skills.map((skill) => ({
              label: skill.name,
              meta: `${skill.proficiency}${skill.is_evidence_backed ? ` · ${skill.evidence_count}× proven` : " · claimed only"}`,
              tone: skill.is_evidence_backed ? ("brand" as const) : ("neutral" as const),
            }))}
          />
        ) : null}
        {tab === "projects" ? (
          <RedirectSection
            icon={<FolderGit2 size={18} />}
            title="Projects"
            body="Projects are edited in the onboarding projects step, which includes technologies, contribution and links."
            count={`${profile.projects.length} projects`}
            to="/onboarding?step=4"
            items={profile.projects.map((project) => ({
              label: project.title,
              meta: [project.category, project.technologies.slice(0, 3).join(", ")]
                .filter(Boolean)
                .join(" · "),
              tone: "neutral" as const,
            }))}
          />
        ) : null}
        {tab === "experience" ? (
          <div className="space-y-5">
            <RedirectSection
              icon={<Briefcase size={18} />}
              title="Experience"
              body="Internships, work, positions of responsibility, certifications and achievements are edited together in step 5."
              count={`${profile.experiences.length} experience · ${profile.certifications.length} certifications · ${profile.achievements.length} achievements`}
              to="/onboarding?step=5"
              items={[
                ...profile.experiences.map((item) => ({
                  label: `${item.title} · ${item.organization}`,
                  meta: titleCase(item.experience_type),
                  tone: "neutral" as const,
                })),
                ...profile.certifications.map((item) => ({
                  label: item.name,
                  meta: item.issuer ?? "Certification",
                  tone: "brand" as const,
                })),
                ...profile.achievements.map((item) => ({
                  label: item.title,
                  meta: titleCase(item.category),
                  tone: "brand" as const,
                })),
              ]}
            />
            <Card className="p-5">
              <SectionHeader
                title="Resume"
                description={
                  profile.resume
                    ? `${profile.resume.original_filename} · uploaded ${formatDate(profile.resume.uploaded_at)} · quality ${profile.resume.quality_score ?? "-"}/100`
                    : "No resume uploaded."
                }
                icon={<FileText size={17} />}
                action={
                  <Link to="/onboarding?step=6">
                    <Button size="sm" variant="outline">
                      {profile.resume ? "Replace resume" : "Upload resume"}
                    </Button>
                  </Link>
                }
              />
              {profile.resume?.parse_status === "failed" ? (
                <InlineNote tone="warn">
                  The last upload could not be parsed: {profile.resume.parse_error}
                </InlineNote>
              ) : null}
            </Card>
          </div>
        ) : null}
        {tab === "preferences" ? (
          <RedirectSection
            icon={<Target size={18} />}
            title="Career targets"
            body="Change which roles you are measured against. Updating this reshapes the dashboard and regenerates your roadmap."
            count={`${profile.preferences.length} target roles`}
            to="/onboarding?step=7"
            items={profile.preferences.map((item) => ({
              label: item.role_name,
              meta: item.is_primary ? "Primary target" : item.domain_name,
              tone: item.is_primary ? ("forest" as const) : ("neutral" as const),
            }))}
          />
        ) : null}
        {tab === "account" ? (
          <AccountSection settings={settings} onReload={load} />
        ) : null}
      </div>
    </AppShell>
  );
}

// ---------------------------------------------------------------------------
// Profile (personal + academics summary)
// ---------------------------------------------------------------------------
function ProfileSection({
  profile,
  onSaved,
}: {
  profile: FullProfile;
  onSaved: (message: string, recalculated: string[]) => Promise<void>;
}) {
  const { push } = useToast();
  const [form, setForm] = useState({
    full_name: String(profile.user.full_name ?? ""),
    email: String(profile.user.email ?? ""),
    phone: profile.profile.phone ?? "",
    location: profile.profile.location ?? "",
    college: profile.profile.college ?? "",
    degree: profile.profile.degree ?? "",
    branch: profile.profile.branch ?? "",
    graduation_year: profile.profile.graduation_year ?? new Date().getFullYear() + 1,
    current_academic_year: profile.profile.current_academic_year ?? "3rd Year",
    cgpa: profile.profile.cgpa ?? "",
    cgpa_scale: profile.profile.cgpa_scale ?? 10,
    headline: profile.profile.headline ?? "",
    bio: profile.profile.bio ?? "",
  });
  const [links, setLinks] = useState({
    github_url: profile.profile.github_url ?? "",
    linkedin_url: profile.profile.linkedin_url ?? "",
    portfolio_url: profile.profile.portfolio_url ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [savingLinks, setSavingLinks] = useState(false);

  const savePersonal = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const result = await api.updateSection("personal", {
        ...form,
        phone: form.phone || null,
        location: form.location || null,
        headline: form.headline || null,
        bio: form.bio || null,
        graduation_year: Number(form.graduation_year),
        cgpa: form.cgpa === "" ? null : Number(form.cgpa),
        cgpa_scale: Number(form.cgpa_scale),
      });
      await onSaved(result.message, result.recalculated_roles);
    } catch (err) {
      push({
        title: "Could not save",
        description: err instanceof ApiError ? err.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setSaving(false);
    }
  };

  const saveLinks = async () => {
    setSavingLinks(true);
    try {
      const result = await api.updateSection("preferences", {
        github_url: links.github_url || null,
        linkedin_url: links.linkedin_url || null,
        portfolio_url: links.portfolio_url || null,
        other_links: [],
        role_ids: profile.preferences.map((item) => item.role_id),
        primary_role_id:
          profile.preferences.find((item) => item.is_primary)?.role_id ??
          profile.preferences[0]?.role_id ??
          null,
      });
      await onSaved(result.message, result.recalculated_roles);
    } catch (err) {
      push({
        title: "Could not save links",
        description: err instanceof ApiError ? err.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setSavingLinks(false);
    }
  };

  return (
    <div className="space-y-5">
      <Card className="p-5">
        <SectionHeader
          title="Personal & academic information"
          description="Used across every rubric. Academic details feed the Academic Profile component."
          icon={<UserCircle2 size={17} />}
        />
        <form onSubmit={savePersonal} className="mt-4 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <TextInput
              label="Full name"
              required
              value={form.full_name}
              onChange={(event) => setForm({ ...form, full_name: event.target.value })}
            />
            <TextInput
              label="Email"
              required
              type="email"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
            />
            <TextInput
              label="Phone"
              value={form.phone}
              onChange={(event) => setForm({ ...form, phone: event.target.value })}
            />
            <TextInput
              label="Location"
              value={form.location}
              onChange={(event) => setForm({ ...form, location: event.target.value })}
            />
            <TextInput
              label="College / University"
              required
              className="sm:col-span-2"
              value={form.college}
              onChange={(event) => setForm({ ...form, college: event.target.value })}
            />
            <TextInput
              label="Degree"
              required
              value={form.degree}
              onChange={(event) => setForm({ ...form, degree: event.target.value })}
            />
            <TextInput
              label="Branch"
              required
              value={form.branch}
              onChange={(event) => setForm({ ...form, branch: event.target.value })}
            />
            <TextInput
              label="Graduation year"
              required
              type="number"
              value={form.graduation_year}
              onChange={(event) => setForm({ ...form, graduation_year: event.target.value as any })}
            />
            <TextInput
              label="Current academic year"
              required
              value={form.current_academic_year}
              onChange={(event) => setForm({ ...form, current_academic_year: event.target.value })}
            />
            <TextInput
              label="CGPA"
              type="number"
              step="0.01"
              value={form.cgpa}
              hint="Optional. Several finance and consulting rubrics screen on it."
              onChange={(event) => setForm({ ...form, cgpa: event.target.value as any })}
            />
            <TextInput
              label="CGPA scale"
              type="number"
              value={form.cgpa_scale}
              onChange={(event) => setForm({ ...form, cgpa_scale: event.target.value as any })}
            />
            <TextInput
              label="Headline"
              className="sm:col-span-2"
              value={form.headline}
              onChange={(event) => setForm({ ...form, headline: event.target.value })}
            />
          </div>

          <div className="flex justify-end border-t border-line pt-4">
            <Button type="submit" loading={saving}>
              Save changes
            </Button>
          </div>
        </form>
      </Card>

      <Card className="p-5">
        <SectionHeader title="Portfolio links" icon={<Link2 size={17} />} />
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <TextInput
            label="GitHub"
            value={links.github_url}
            onChange={(event) => setLinks({ ...links, github_url: event.target.value })}
          />
          <TextInput
            label="LinkedIn"
            value={links.linkedin_url}
            onChange={(event) => setLinks({ ...links, linkedin_url: event.target.value })}
          />
          <TextInput
            label="Portfolio"
            value={links.portfolio_url}
            onChange={(event) => setLinks({ ...links, portfolio_url: event.target.value })}
          />
        </div>
        <div className="mt-4 flex justify-end border-t border-line pt-4">
          <Button loading={savingLinks} onClick={saveLinks} variant="outline">
            Save links
          </Button>
        </div>
      </Card>

      <Card className="p-5">
        <SectionHeader
          title="Education history"
          description={`${profile.academics.length} qualification(s) on record.`}
          icon={<GraduationCap size={17} />}
          action={
            <Link to="/onboarding?step=2">
              <Button size="sm" variant="outline">
                Edit education
              </Button>
            </Link>
          }
        />
        <div className="mt-4 space-y-2">
          {profile.academics.map((entry) => (
            <div key={entry.id} className="rounded-xl border border-line bg-surface-muted p-3.5">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-ink-900">{entry.institution}</p>
                  <p className="text-xs text-ink-500">
                    {[entry.degree_or_program, entry.specialization].filter(Boolean).join(" · ")}
                  </p>
                </div>
                <div className="text-right text-xs text-ink-500">
                  {entry.score !== null ? (
                    <p className="font-semibold text-ink-800">
                      {entry.score}
                      {entry.score_type === "percentage" ? "%" : " CGPA"}
                    </p>
                  ) : null}
                  <p>
                    {entry.start_year ?? "?"} - {entry.end_year ?? "present"}
                  </p>
                </div>
              </div>
              {entry.relevant_coursework.length ? (
                <p className="mt-1.5 text-2xs text-ink-400">
                  Coursework: {entry.relevant_coursework.join(", ")}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section summary with a link to the full editor
// ---------------------------------------------------------------------------
function RedirectSection({
  icon,
  title,
  body,
  count,
  to,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  count: string;
  to: string;
  items: { label: string; meta: string; tone: "brand" | "neutral" | "forest" }[];
}) {
  return (
    <Card className="p-5">
      <SectionHeader
        title={title}
        description={count}
        icon={icon}
        action={
          <Link to={to}>
            <Button size="sm">Edit {title.toLowerCase()}</Button>
          </Link>
        }
      />
      <InlineNote tone="info" icon={<SlidersHorizontal size={15} />}>
        {body} Saving there recalculates the affected role scores immediately.
      </InlineNote>

      {items.length ? (
        <div className="mt-4 divide-y divide-line overflow-hidden rounded-xl border border-line">
          {items.map((item, index) => (
            <div
              key={`${item.label}-${index}`}
              className="flex items-center justify-between gap-3 bg-white px-3.5 py-2.5"
            >
              <p className="min-w-0 truncate text-sm font-medium text-ink-800">{item.label}</p>
              <Badge tone={item.tone} className="shrink-0 capitalize">
                {item.meta}
              </Badge>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-sm text-ink-400">Nothing recorded yet.</p>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Account: preferences + password
// ---------------------------------------------------------------------------
function AccountSection({
  settings,
  onReload,
}: {
  settings: SettingsPayload;
  onReload: () => Promise<void>;
}) {
  const { push } = useToast();
  const [local, setLocal] = useState(settings);
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwords, setPasswords] = useState({
    current_password: "",
    new_password: "",
    confirm_new_password: "",
  });
  const [passwordErrors, setPasswordErrors] = useState<Record<string, string>>({});

  const updateSetting = async (patch: Partial<SettingsPayload>) => {
    const next = { ...local, ...patch };
    setLocal(next);
    try {
      const saved = await api.updateSettings(patch);
      setLocal(saved);
      await onReload();
    } catch (err) {
      setLocal(local);
      push({
        title: "Could not save that setting",
        description: err instanceof ApiError ? err.message : "Please try again.",
        variant: "error",
      });
    }
  };

  const changePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    const errors: Record<string, string> = {};
    if (!passwords.current_password) errors.current_password = "Required";
    if (passwords.new_password.length < 8) errors.new_password = "At least 8 characters";
    if (!/\d/.test(passwords.new_password) || !/[A-Za-z]/.test(passwords.new_password))
      errors.new_password = "Use at least one letter and one number";
    if (passwords.new_password !== passwords.confirm_new_password)
      errors.confirm_new_password = "Passwords do not match";
    setPasswordErrors(errors);
    if (Object.keys(errors).length) return;

    setSavingPassword(true);
    try {
      await api.changePassword(passwords);
      setPasswords({ current_password: "", new_password: "", confirm_new_password: "" });
      push({ title: "Password updated", variant: "success" });
    } catch (err) {
      push({
        title: "Could not change your password",
        description: err instanceof ApiError ? err.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <div className="space-y-5">
      <Card className="p-5">
        <SectionHeader
          title="Preferences"
          description="Notification and assessment behaviour."
          icon={<SlidersHorizontal size={17} />}
        />
        <div className="mt-2 divide-y divide-line">
          <Toggle
            checked={local.auto_recalculate_scores}
            onChange={(next) => updateSetting({ auto_recalculate_scores: next })}
            label="Recalculate scores automatically"
            description="Rescore the affected roles whenever you change your profile."
          />
          <Toggle
            checked={local.email_notifications}
            onChange={(next) => updateSetting({ email_notifications: next })}
            label="Email notifications"
            description="Stored as a preference. Email delivery is not part of this release."
          />
          <Toggle
            checked={local.weekly_progress_digest}
            onChange={(next) => updateSetting({ weekly_progress_digest: next })}
            label="Weekly progress digest"
            description="Stored as a preference for a future release."
          />
          <Toggle
            checked={local.roadmap_reminders}
            onChange={(next) => updateSetting({ roadmap_reminders: next })}
            label="Roadmap reminders"
            description="Stored as a preference for a future release."
          />
        </div>
        <InlineNote tone="info">
          Notification toggles are saved to your account but no emails are sent in this phase - the
          delivery pipeline is not built yet.
        </InlineNote>
      </Card>

      <Card className="p-5">
        <SectionHeader
          title="Change password"
          description="Passwords are hashed with Argon2id. Your current password is required."
          icon={<KeyRound size={17} />}
        />
        <form onSubmit={changePassword} className="mt-4 max-w-md space-y-4">
          <Field label="Current password" required error={passwordErrors.current_password}>
            <input
              type="password"
              autoComplete="current-password"
              className="input-base"
              value={passwords.current_password}
              onChange={(event) =>
                setPasswords({ ...passwords, current_password: event.target.value })
              }
            />
          </Field>
          <Field label="New password" required error={passwordErrors.new_password}>
            <input
              type="password"
              autoComplete="new-password"
              className="input-base"
              value={passwords.new_password}
              onChange={(event) => setPasswords({ ...passwords, new_password: event.target.value })}
            />
          </Field>
          <Field label="Confirm new password" required error={passwordErrors.confirm_new_password}>
            <input
              type="password"
              autoComplete="new-password"
              className="input-base"
              value={passwords.confirm_new_password}
              onChange={(event) =>
                setPasswords({ ...passwords, confirm_new_password: event.target.value })
              }
            />
          </Field>
          <Button type="submit" loading={savingPassword} icon={<Award size={15} />}>
            Update password
          </Button>
        </form>
      </Card>
    </div>
  );
}
