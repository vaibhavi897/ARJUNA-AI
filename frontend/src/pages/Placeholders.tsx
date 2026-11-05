/**
 * Placeholder modules reserved for teammates.
 *
 * These are deliberately honest: they state that the feature is not built yet
 * rather than showing fake data. Routing and the shell are real, so another
 * developer can drop a feature in without touching navigation.
 */
import { Link } from "react-router-dom";
import {
  BookOpenCheck,
  ClipboardList,
  Compass,
  Construction,
  FileText,
  LayoutDashboard,
  TrendingUp,
} from "lucide-react";
import { AppShell } from "../components/layout";
import { Badge, Button, Card } from "../components/ui";

function Placeholder({
  title,
  icon,
  summary,
  planned,
  dataReady,
  integrationNote,
}: {
  title: string;
  icon: React.ReactNode;
  summary: string;
  planned: string[];
  dataReady: string[];
  integrationNote: string;
}) {
  return (
    <AppShell title={title} subtitle="Reserved module - not implemented in this phase">
      <div className="mx-auto max-w-4xl space-y-5">
        <Card className="overflow-hidden p-0">
          <div className="mesh-forest relative px-6 py-8 text-white">
            <div className="absolute inset-0 grid-lines opacity-[0.06]" aria-hidden />
            <div className="relative flex items-start gap-4">
              <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-white/[0.12] text-white ring-1 ring-white/15">
                {icon}
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-display text-xl font-extrabold">{title}</h2>
                  <Badge tone="forest" className="border-white/20 bg-white/15 text-white">
                    <Construction size={11} /> Not built yet
                  </Badge>
                </div>
                <p className="mt-2 max-w-xl text-sm leading-relaxed text-white/70">{summary}</p>
              </div>
            </div>
          </div>
        </Card>

        <div className="grid gap-5 md:grid-cols-2">
          <Card className="p-5">
            <p className="section-label">Planned for this module</p>
            <ul className="mt-3 space-y-2">
              {planned.map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm text-ink-600">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-sage-400" />
                  {item}
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-5">
            <p className="section-label">Already available to build on</p>
            <ul className="mt-3 space-y-2">
              {dataReady.map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm text-ink-600">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-400" />
                  {item}
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <Card className="p-5">
          <p className="section-label">Integration note for teammates</p>
          <p className="mt-2 text-sm leading-relaxed text-ink-600">{integrationNote}</p>
        </Card>

        <div className="flex flex-wrap gap-2">
          <Link to="/app/dashboard">
            <Button icon={<LayoutDashboard size={16} />}>Back to dashboard</Button>
          </Link>
          <a href="/docs" target="_blank" rel="noopener noreferrer">
            <Button variant="outline">Open API docs</Button>
          </a>
        </div>
      </div>
    </AppShell>
  );
}

export function PlacementPrep() {
  return (
    <Placeholder
      title="Placement Prep"
      icon={<BookOpenCheck size={22} />}
      summary="Structured preparation tracks - aptitude, DSA, finance and case practice - mapped to the gaps already identified in your assessment."
      planned={[
        "Topic-wise question banks per career domain",
        "Timed mock tests with score history",
        "Company-specific preparation tracks",
        "Practice sessions linked to your weakest rubric components",
      ]}
      dataReady={[
        "Per-role skill gaps with points lost (skill_gap_analysis)",
        "Role rubrics with expected proficiency per skill",
        "Roadmap tasks and their completion state",
        "Activity log to record practice sessions",
      ]}
      integrationNote="Add routes under a new backend module (for example app/modules/prep) and a page under src/pages. The sidebar entry and route already exist, so only the module itself needs writing. Read gaps from GET /api/dashboard/roles/{slug} rather than recomputing them."
    />
  );
}

export function ResumeBuilder() {
  return (
    <Placeholder
      title="Resume Builder"
      icon={<FileText size={22} />}
      summary="Generate a role-targeted resume from the profile data already stored, using the quality checks the analyser scores against."
      planned={[
        "Template selection with live preview",
        "Role-targeted keyword suggestions",
        "Bullet rewriting help for quantified impact",
        "Export to PDF and DOCX",
      ]}
      dataReady={[
        "Full structured profile at GET /api/profile",
        "Resume quality checks and missing keywords per role",
        "Parsed text and sections from previous uploads",
        "Role resume_keywords lists in job_roles",
      ]}
      integrationNote="The quality rubric in app/modules/resume/quality.py is the contract to build against - generate resumes that pass those checks. Resume parsing and storage already work, so the builder only needs a render and export path."
    />
  );
}

export function AIAssessment() {
  return (
    <Placeholder
      title="AI Assessment"
      icon={<ClipboardList size={22} />}
      summary="Interactive assessments - adaptive quizzes and mock interviews - that produce verified evidence rather than self-reported proficiency."
      planned={[
        "Adaptive skill quizzes that validate claimed proficiency",
        "Mock interview practice with structured feedback",
        "Verified-skill badges feeding back into scoring",
        "Per-attempt analytics",
      ]}
      dataReady={[
        "Scoring engine with a pluggable evidence model",
        "student_skills.evidence_count and is_evidence_backed columns",
        "Assessment snapshots and versioning in role_assessments",
        "Per-component explanations in assessment_score_breakdowns",
      ]}
      integrationNote="The scoring engine already separates claimed from evidence-backed skills. A verified quiz result should increment evidence through the same path projects use, so no scoring change is required - see app/modules/profile/skills.py."
    />
  );
}

export function CareerPaths() {
  return (
    <Placeholder
      title="Career Paths"
      icon={<Compass size={22} />}
      summary="Explore roles in depth: what the work involves, the full rubric, typical progression and what it would take you to get there."
      planned={[
        "Role explorer with full rubric transparency",
        "Side-by-side role comparison",
        "Progression maps and adjacent-role suggestions",
        "What-if simulation: see a score change before doing the work",
      ]}
      dataReady={[
        "GET /api/catalog/domains for all domains and roles",
        "GET /api/catalog/roles/{slug} for a role's full rubric and weights",
        "Your current score against every active role",
        "Domain averages already computed on the dashboard",
      ]}
      integrationNote="Every rubric is already exposed read-only through the catalogue endpoints, including weights and expected proficiency. A what-if simulator can call the scoring engine with a modified snapshot without writing to the database."
    />
  );
}

export function MyProgress() {
  return (
    <Placeholder
      title="My Progress"
      icon={<TrendingUp size={22} />}
      summary="A dedicated progress view - streaks, goals and milestone tracking on top of the assessment snapshots already being stored."
      planned={[
        "Goal setting with target scores and deadlines",
        "Streaks and consistency tracking",
        "Milestone timeline across all roles",
        "Exportable progress report",
      ]}
      dataReady={[
        "Full assessment history per role with version numbers",
        "Completed roadmap tasks with completion timestamps",
        "Activity log covering every profile change",
        "Score deltas computed on each assessment",
      ]}
      integrationNote="The dashboard already renders a condensed version of this from GET /api/dashboard (the progress object). This module can use the same payload plus GET /api/activity for the full feed."
    />
  );
}
