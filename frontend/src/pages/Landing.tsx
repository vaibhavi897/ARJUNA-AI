/** Public marketing page. */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  Brain,
  Briefcase,
  CheckCircle2,
  FileSearch,
  GaugeCircle,
  LineChart,
  ListChecks,
  Lock,
  Sparkles,
  Target,
  UserCircle2,
} from "lucide-react";
import { PublicFooter, PublicNav } from "../components/layout";
import { Badge, Button, Card } from "../components/ui";
import { api, type CareerDomain } from "../lib/api";

const STEPS = [
  {
    icon: <UserCircle2 size={20} />,
    title: "Build your profile",
    body: "A guided seven-step onboarding captures your academics, skills, projects, internships and target roles. Each step saves on its own, so you can stop and resume any time.",
  },
  {
    icon: <FileSearch size={20} />,
    title: "Upload your resume",
    body: "We extract the text, identify skills, education, projects and achievements, then show you exactly what was found. Nothing is imported into your profile until you approve it.",
  },
  {
    icon: <GaugeCircle size={20} />,
    title: "Get role-wise scores",
    body: "Every role is scored against its own rubric, not one generic formula. You see the score, the weights behind it, and the reasoning for every component.",
  },
  {
    icon: <ListChecks size={20} />,
    title: "Work the roadmap",
    body: "Gaps become prioritised actions with a reason, a duration and the points at stake. Tick them off and your scores update with the next assessment.",
  },
];

const FEATURES = [
  {
    icon: <Target size={18} />,
    title: "Separate score per role",
    body: "Software Engineering, Data Analytics, AI/ML, Investment Banking, Corporate Risk and Management Consulting each have distinct weights and skill requirements.",
  },
  {
    icon: <CheckCircle2 size={18} />,
    title: "Claims versus evidence",
    body: "Listing a skill is not the same as proving it. A skill demonstrated in a project or internship earns close to full credit; a claimed-only skill earns materially less.",
  },
  {
    icon: <BarChart3 size={18} />,
    title: "Explainable, never random",
    body: "Each component states what it measured and why. Open a role to see the points earned per component and the skills behind the number.",
  },
  {
    icon: <FileSearch size={18} />,
    title: "Resume analysis",
    body: "Quality scoring across sections, bullet formatting, action verbs, quantified impact and the role keywords your resume is missing.",
  },
  {
    icon: <LineChart size={18} />,
    title: "Progress over time",
    body: "Every assessment is stored as a snapshot, so you can see how each role score moved after you acted on the roadmap.",
  },
  {
    icon: <Lock size={18} />,
    title: "Your data stays yours",
    body: "Passwords are hashed with Argon2, sessions use signed tokens, and every record is scoped to your authenticated account.",
  },
];

const BENEFITS = [
  "Know which roles you are actually competitive for before applications open",
  "Stop guessing what to learn next - the roadmap is ordered by points at stake",
  "See the exact skills a role expects, at the proficiency it expects them",
  "Turn listed skills into proven skills with targeted project suggestions",
  "Fix the resume problems recruiters screen on, with specifics",
  "Track whether the work you put in is actually moving your scores",
];

export default function Landing() {
  const [domains, setDomains] = useState<CareerDomain[]>([]);

  // Pulled live so the marketing page reflects the roles actually configured.
  useEffect(() => {
    let cancelled = false;
    api
      .domains()
      .then((data) => {
        if (!cancelled) setDomains(data);
      })
      .catch(() => {
        /* the landing page still works without the catalogue */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const roleCount = domains.reduce((total, domain) => total + domain.roles.length, 0);

  return (
    <div className="min-h-screen bg-white">
      <PublicNav />

      {/* ---------------- Hero ---------------- */}
      <section className="relative overflow-hidden pt-24 sm:pt-28">
        <div className="absolute inset-0 mesh-sage" aria-hidden />
        <div className="absolute inset-0 grid-lines opacity-40" aria-hidden />
        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 pb-16 pt-10 sm:px-6 lg:grid-cols-2 lg:gap-16 lg:px-8 lg:pb-24">
          <div className="animate-fade-up">
            <Badge tone="brand" className="mb-5">
              <Sparkles size={12} /> Built for students, not placement cells
            </Badge>
            <h1 className="text-balance font-display text-4xl font-extrabold leading-[1.08] tracking-tight text-forest-900 sm:text-5xl lg:text-[3.4rem]">
              Know exactly how{" "}
              <span className="relative inline-block">
                <span className="relative z-10 text-brand-600">placement ready</span>
                <span
                  className="absolute inset-x-0 bottom-1 z-0 h-3 rounded-sm bg-brand-200/70"
                  aria-hidden
                />
              </span>{" "}
              you are, role by role.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-ink-600 sm:text-lg">
              Arjuna AI reads your profile, projects, experience and resume, then scores your
              readiness for each target role against that role's own rubric. You get the number,
              the reasoning behind it, and an ordered plan to raise it.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/register">
                <Button size="lg" icon={<ArrowRight size={17} />}>
                  Start my assessment
                </Button>
              </Link>
              <Link to="/login">
                <Button size="lg" variant="outline">
                  I already have an account
                </Button>
              </Link>
            </div>

            <dl className="mt-10 grid max-w-lg grid-cols-3 gap-4 border-t border-line pt-6">
              {[
                { value: roleCount ? `${roleCount}` : "16", label: "Roles scored separately" },
                { value: domains.length ? `${domains.length}` : "8", label: "Career domains" },
                { value: "7", label: "Scoring components per role" },
              ].map((stat) => (
                <div key={stat.label}>
                  <dt className="font-display text-2xl font-extrabold text-forest-800">
                    {stat.value}
                  </dt>
                  <dd className="mt-0.5 text-xs leading-snug text-ink-500">{stat.label}</dd>
                </div>
              ))}
            </dl>
          </div>

          {/* Mock dashboard preview */}
          <div className="relative animate-fade-up [animation-delay:120ms]">
            <div className="absolute -inset-4 rounded-3xl bg-brand-400/10 blur-2xl" aria-hidden />
            <Card className="relative overflow-hidden p-5 shadow-float">
              <div className="flex items-center justify-between border-b border-line pb-4">
                <div>
                  <p className="section-label">Career readiness</p>
                  <p className="mt-0.5 font-display text-lg font-bold">Role-wise breakdown</p>
                </div>
                <Badge tone="brand">Live example</Badge>
              </div>

              <div className="mt-5 space-y-3.5">
                {[
                  { role: "Software Engineering", score: 83, band: "Strong" },
                  { role: "Data Analytics", score: 76, band: "Strong" },
                  { role: "AI / Machine Learning", score: 71, band: "Strong" },
                  { role: "Management Consulting", score: 58, band: "Developing" },
                  { role: "Corporate Risk", score: 52, band: "Developing" },
                  { role: "Investment Banking", score: 43, band: "Emerging" },
                ].map((row, index) => (
                  <div key={row.role}>
                    <div className="mb-1.5 flex items-baseline justify-between gap-2">
                      <span className="truncate text-sm font-medium text-ink-700">{row.role}</span>
                      <span className="shrink-0 text-sm font-bold tabular-nums text-forest-800">
                        {row.score}
                        <span className="text-xs font-medium text-ink-400">/100</span>
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-sage-200">
                      <div
                        className="h-full rounded-full transition-[width] duration-1000 ease-smooth"
                        style={{
                          width: `${row.score}%`,
                          backgroundColor:
                            row.score >= 70 ? "#187C4F" : row.score >= 50 ? "#C9872B" : "#C0493D",
                          transitionDelay: `${index * 90}ms`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-5 rounded-xl border border-brand-100 bg-brand-50/70 p-3.5">
                <p className="flex items-start gap-2 text-xs leading-relaxed text-brand-800">
                  <Brain size={14} className="mt-0.5 shrink-0" />
                  <span>
                    <strong className="font-semibold">Insight:</strong> your technical profile is
                    stronger than your finance profile. A financial modelling project would raise
                    Investment Banking readiness the fastest.
                  </span>
                </p>
              </div>

              <p className="mt-3 text-center text-2xs text-ink-400">
                Illustrative figures. Your scores are computed from your own profile.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* ---------------- How it works ---------------- */}
      <section id="how-it-works" className="scroll-mt-20 border-y border-line bg-white py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="section-label">How it works</p>
            <h2 className="mt-2 text-balance font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
              Four steps from profile to plan
            </h2>
            <p className="mt-3 text-base text-ink-600">
              No generic resume grade. Arjuna AI evaluates you the way a specific role would.
            </p>
          </div>

          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, index) => (
              <Card key={step.title} interactive className="relative p-5">
                <span className="absolute right-4 top-4 font-display text-4xl font-extrabold text-sage-200">
                  {index + 1}
                </span>
                <span className="relative grid h-11 w-11 place-items-center rounded-2xl bg-forest-800 text-white">
                  {step.icon}
                </span>
                <h3 className="relative mt-4 text-base font-bold">{step.title}</h3>
                <p className="relative mt-2 text-sm leading-relaxed text-ink-600">{step.body}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- Features ---------------- */}
      <section id="features" className="scroll-mt-20 bg-surface-sunken py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="section-label">Capabilities</p>
            <h2 className="mt-2 text-balance font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
              Scoring you can argue with
            </h2>
            <p className="mt-3 text-base text-ink-600">
              Every number is traceable to a rule, a weight and your own data.
            </p>
          </div>

          <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <Card key={feature.title} interactive className="p-5">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-600">
                  {feature.icon}
                </span>
                <h3 className="mt-3.5 text-base font-bold">{feature.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{feature.body}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- Domains ---------------- */}
      <section id="domains" className="scroll-mt-20 border-y border-line bg-white py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="max-w-2xl">
              <p className="section-label">Supported career domains</p>
              <h2 className="mt-2 text-balance font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
                Technology and finance, judged on their own terms
              </h2>
              <p className="mt-3 text-base text-ink-600">
                Each role carries its own rubric: required skills, expected proficiency, CGPA
                expectations, project and internship norms, and domain keywords.
              </p>
            </div>
            <Link to="/register">
              <Button variant="outline" icon={<ArrowRight size={16} />}>
                See your scores
              </Button>
            </Link>
          </div>

          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {(domains.length ? domains : FALLBACK_DOMAINS).map((domain) => (
              <Card key={domain.slug} interactive className="flex flex-col p-5">
                <span
                  className="mb-3 inline-block h-1.5 w-10 rounded-full"
                  style={{ backgroundColor: domain.accent_color ?? "#187C4F" }}
                />
                <h3 className="text-base font-bold">{domain.name}</h3>
                <p className="mt-1.5 flex-1 text-sm leading-relaxed text-ink-600">
                  {domain.description}
                </p>
                <ul className="mt-3.5 space-y-1.5 border-t border-line pt-3.5">
                  {domain.roles.slice(0, 3).map((role) => (
                    <li key={role.slug} className="flex items-start gap-1.5 text-xs text-ink-600">
                      <Briefcase size={12} className="mt-0.5 shrink-0 text-brand-500" />
                      <span>{role.name}</span>
                    </li>
                  ))}
                  {domain.roles.length > 3 ? (
                    <li className="pl-5 text-xs font-medium text-ink-400">
                      +{domain.roles.length - 3} more
                    </li>
                  ) : null}
                </ul>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- Benefits ---------------- */}
      <section id="benefits" className="scroll-mt-20 bg-surface-sunken py-16 lg:py-24">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:items-center lg:px-8">
          <div>
            <p className="section-label">What students get</p>
            <h2 className="mt-2 text-balance font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
              Clarity instead of vague advice
            </h2>
            <p className="mt-3 text-base text-ink-600">
              "Improve your skills" is not actionable. "Your Investment Banking score loses 11
              points because LBO modelling is missing" is.
            </p>
            <ul className="mt-7 space-y-3">
              {BENEFITS.map((benefit) => (
                <li key={benefit} className="flex items-start gap-3">
                  <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-brand-500" />
                  <span className="text-sm leading-relaxed text-ink-700">{benefit}</span>
                </li>
              ))}
            </ul>
          </div>

          <Card className="overflow-hidden p-0 shadow-float">
            <div className="mesh-forest px-6 py-7 text-white">
              <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-white/50">
                Sample roadmap action
              </p>
              <h3 className="mt-2 font-display text-xl font-bold text-white">Learn LBO Modelling</h3>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-full bg-white/15 px-2.5 py-1 text-2xs font-semibold">
                  High priority
                </span>
                <span className="rounded-full bg-white/15 px-2.5 py-1 text-2xs font-semibold">
                  4-8 weeks
                </span>
                <span className="rounded-full bg-brand-400 px-2.5 py-1 text-2xs font-bold text-forest-900">
                  +5.4 points
                </span>
              </div>
            </div>
            <div className="space-y-4 p-6">
              <div>
                <p className="section-label">Why this is recommended</p>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-700">
                  LBO Modelling is a preferred skill for Investment Banking Analyst at beginner
                  level, and it is missing from your profile. Your Financial Modelling and Valuation
                  skills already clear the bar, so this is the cheapest remaining gain.
                </p>
              </div>
              <div className="rounded-xl bg-sage-50 p-4">
                <p className="section-label">Expected improvement area</p>
                <p className="mt-1 text-sm font-semibold text-forest-800">Role Skills Match</p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-sage-200">
                  <div className="h-full w-[72%] rounded-full bg-brand-500" />
                </div>
                <p className="mt-2 text-xs text-ink-500">
                  Role Skills Match currently earns 20.2 of 28 available points.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* ---------------- CTA ---------------- */}
      <section className="relative overflow-hidden bg-white py-16 lg:py-20">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <Card className="relative overflow-hidden border-0 p-0 shadow-float">
            <div className="mesh-forest px-6 py-12 text-center sm:px-12">
              <h2 className="text-balance font-display text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
                Find out where you actually stand
              </h2>
              <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-white/70 sm:text-base">
                Create a free student account, complete onboarding, and get a separate readiness
                score for every role you care about - with the reasoning attached.
              </p>
              <div className="mt-7 flex flex-wrap justify-center gap-3">
                <Link to="/register">
                  <Button size="lg" variant="secondary" icon={<ArrowRight size={17} />}>
                    Create my free account
                  </Button>
                </Link>
                <Link to="/login">
                  <Button
                    size="lg"
                    variant="ghost"
                    className="text-white hover:bg-white/10 hover:text-white"
                  >
                    Log in
                  </Button>
                </Link>
              </div>
              <p className="mt-5 text-2xs text-white/45">
                Students only in this release. No recruiter access exists yet.
              </p>
            </div>
          </Card>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}

/** Shown only if the catalogue request fails, so the page never looks broken. */
const FALLBACK_DOMAINS: CareerDomain[] = [
  {
    id: 1,
    name: "Software Engineering",
    slug: "software-engineering",
    description: "Building and shipping software systems, from APIs to full products.",
    icon: null,
    accent_color: "#1B7A4B",
    display_order: 1,
    roles: [],
  },
  {
    id: 2,
    name: "Data Analytics",
    slug: "data-analytics",
    description: "Turning raw data into decisions through analysis and reporting.",
    icon: null,
    accent_color: "#2E8B57",
    display_order: 2,
    roles: [],
  },
  {
    id: 3,
    name: "Investment Banking",
    slug: "investment-banking",
    description: "Advisory, valuation and capital raising for corporate clients.",
    icon: null,
    accent_color: "#0F5132",
    display_order: 3,
    roles: [],
  },
  {
    id: 4,
    name: "Management Consulting",
    slug: "management-consulting",
    description: "Structured problem solving for strategy and operations questions.",
    icon: null,
    accent_color: "#246B4A",
    display_order: 4,
    roles: [],
  },
];
