/** Login and registration screens (student only). */
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  AtSign,
  BadgeCheck,
  CheckCircle2,
  Eye,
  EyeOff,
  Lock,
  Mail,
  ShieldCheck,
  User,
} from "lucide-react";
import { Logo } from "../components/layout";
import { Badge, Button, Field, TextInput } from "../components/ui";
import { ApiError, api } from "../lib/api";
import { useAuth, useToast } from "../lib/auth";
import { cn } from "../lib/utils";

const SIDE_POINTS = [
  "A separate readiness score for each role you target",
  "Every point traced back to a rule and your own data",
  "Resume analysis you review before anything is imported",
  "A roadmap ordered by the points at stake",
];

function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_minmax(0,560px)]">
      {/* Brand panel */}
      <div className="relative hidden overflow-hidden mesh-forest lg:block">
        <div className="absolute inset-0 grid-lines opacity-[0.07]" aria-hidden />
        <div className="relative flex h-full flex-col justify-between p-12">
          <Link to="/" aria-label="Arjuna AI home">
            <Logo variant="light" size="lg" />
          </Link>

          <div className="max-w-md">
            <h2 className="text-balance font-display text-3xl font-extrabold leading-tight text-white">
              Placement readiness, measured role by role.
            </h2>
            <ul className="mt-7 space-y-3.5">
              {SIDE_POINTS.map((point) => (
                <li key={point} className="flex items-start gap-3">
                  <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-brand-400" />
                  <span className="text-sm leading-relaxed text-white/75">{point}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex items-center gap-2 text-xs text-white/45">
            <ShieldCheck size={14} />
            Passwords hashed with Argon2. Your records are scoped to your account.
          </div>
        </div>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center bg-white px-4 py-10 sm:px-8">
        <div className="w-full max-w-md animate-fade-up">
          <div className="lg:hidden">
            <Link to="/" aria-label="Arjuna AI home">
              <Logo />
            </Link>
          </div>
          <div className="mt-8 lg:mt-0">
            <h1 className="font-display text-2xl font-extrabold tracking-tight sm:text-3xl">
              {title}
            </h1>
            <p className="mt-1.5 text-sm text-ink-500">{subtitle}</p>
          </div>
          <div className="mt-7">{children}</div>
          <div className="mt-6 text-center text-sm text-ink-500">{footer}</div>
        </div>
      </div>
    </div>
  );
}

function PasswordInput({
  label,
  value,
  onChange,
  error,
  autoComplete,
  hint,
  id,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  error?: string;
  autoComplete?: string;
  hint?: string;
  id: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <Field label={label} error={error} hint={hint} required htmlFor={id}>
      <div className="relative">
        <Lock size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" />
        <input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          autoComplete={autoComplete}
          onChange={(event) => onChange(event.target.value)}
          className={cn("input-base pl-9 pr-11", error && "input-error")}
        />
        <button
          type="button"
          onClick={() => setVisible((current) => !current)}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-ink-400 transition-colors hover:bg-sage-100 hover:text-ink-700"
          aria-label={visible ? "Hide password" : "Show password"}
        >
          {visible ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      </div>
    </Field>
  );
}

// ---------------------------------------------------------------------------
// Login
// ---------------------------------------------------------------------------
export function Login() {
  const navigate = useNavigate();
  const { signIn, user } = useAuth();
  const { push } = useToast();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      navigate(user.onboarding_completed ? "/app/dashboard" : "/onboarding", { replace: true });
    }
  }, [user, navigate]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const nextErrors: Record<string, string> = {};
    if (!identifier.trim()) nextErrors.identifier = "Enter your email or username";
    if (!password) nextErrors.password = "Enter your password";
    setErrors(nextErrors);
    setFormError(null);
    if (Object.keys(nextErrors).length) return;

    setSubmitting(true);
    try {
      const response = await api.login({ identifier, password });
      signIn(response);
      push({ title: `Welcome back, ${response.user.full_name.split(" ")[0]}`, variant: "success" });
      navigate(response.next_route.startsWith("/app") ? response.next_route : response.next_route, {
        replace: true,
      });
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Could not sign in. Please try again.";
      setFormError(message);
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length) {
        setErrors(error.fieldErrors);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to pick up where you left off."
      footer={
        <>
          New to Arjuna AI?{" "}
          <Link to="/register" className="link font-semibold">
            Create a student account
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        {formError ? (
          <div className="flex items-start gap-2.5 rounded-xl border border-danger-500/25 bg-danger-50 px-3.5 py-3 animate-fade-in">
            <AlertCircle size={16} className="mt-0.5 shrink-0 text-danger-500" />
            <p className="text-sm text-danger-700">{formError}</p>
          </div>
        ) : null}

        <TextInput
          label="Email or username"
          required
          icon={<AtSign size={15} />}
          value={identifier}
          autoComplete="username"
          onChange={(event) => setIdentifier(event.target.value)}
          error={errors.identifier}
          placeholder="you@college.edu"
        />

        <PasswordInput
          id="login-password"
          label="Password"
          value={password}
          onChange={setPassword}
          error={errors.password}
          autoComplete="current-password"
        />

        <Button type="submit" size="lg" fullWidth loading={submitting} icon={<ArrowRight size={16} />}>
          {submitting ? "Signing in" : "Sign in"}
        </Button>
      </form>

      <div className="mt-6 rounded-xl border border-line bg-surface-muted p-4">
        <p className="flex items-center gap-1.5 text-xs font-semibold text-ink-700">
          <BadgeCheck size={13} className="text-brand-500" />
          Demo account
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-ink-500">
          Seeded demo students use the password{" "}
          <code className="rounded bg-sage-100 px-1 py-0.5 font-mono text-2xs text-forest-800">
            ArjunaDemo@2026
          </code>
          . Try{" "}
          <button
            type="button"
            className="link font-semibold"
            onClick={() => {
              setIdentifier("aarav.menon@demo.arjuna.ai");
              setPassword("ArjunaDemo@2026");
            }}
          >
            aarav.menon@demo.arjuna.ai
          </button>{" "}
          (technology profile) or{" "}
          <button
            type="button"
            className="link font-semibold"
            onClick={() => {
              setIdentifier("rohan.deshpande@demo.arjuna.ai");
              setPassword("ArjunaDemo@2026");
            }}
          >
            rohan.deshpande@demo.arjuna.ai
          </button>{" "}
          (finance profile).
        </p>
      </div>
    </AuthLayout>
  );
}

// ---------------------------------------------------------------------------
// Register
// ---------------------------------------------------------------------------
type Availability = { checking: boolean; available: boolean | null };

function passwordChecks(value: string) {
  return [
    { label: "At least 8 characters", ok: value.length >= 8 },
    { label: "Contains a letter", ok: /[A-Za-z]/.test(value) },
    { label: "Contains a number", ok: /\d/.test(value) },
  ];
}

export function Register() {
  const navigate = useNavigate();
  const { signIn, user } = useAuth();
  const { push } = useToast();

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    username: "",
    password: "",
    confirm_password: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [emailCheck, setEmailCheck] = useState<Availability>({ checking: false, available: null });
  const [usernameCheck, setUsernameCheck] = useState<Availability>({
    checking: false,
    available: null,
  });
  const timers = useRef<Record<string, number>>({});

  useEffect(() => {
    if (user) {
      navigate(user.onboarding_completed ? "/app/dashboard" : "/onboarding", { replace: true });
    }
  }, [user, navigate]);

  const update = (key: keyof typeof form) => (value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: "" }));
  };

  // Debounced uniqueness checks against the backend.
  const checkAvailability = (field: "email" | "username", value: string) => {
    const setter = field === "email" ? setEmailCheck : setUsernameCheck;
    window.clearTimeout(timers.current[field]);
    if (field === "email" ? !value.includes("@") : value.trim().length < 3) {
      setter({ checking: false, available: null });
      return;
    }
    setter({ checking: true, available: null });
    timers.current[field] = window.setTimeout(async () => {
      try {
        const result = await api.availability(field, value);
        setter({ checking: false, available: result.available });
      } catch {
        setter({ checking: false, available: null });
      }
    }, 450);
  };

  const checks = useMemo(() => passwordChecks(form.password), [form.password]);

  const validate = () => {
    const next: Record<string, string> = {};
    if (form.full_name.trim().length < 2) next.full_name = "Enter your full name";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) next.email = "Enter a valid email address";
    if (!/^[a-zA-Z0-9._-]{3,50}$/.test(form.username.trim()))
      next.username = "3-50 characters: letters, numbers, dots, underscores or hyphens";
    if (!checks.every((check) => check.ok))
      next.password = "Use at least 8 characters with a letter and a number";
    if (form.password !== form.confirm_password)
      next.confirm_password = "Passwords do not match";
    if (emailCheck.available === false) next.email = "An account with this email already exists";
    if (usernameCheck.available === false) next.username = "That username is already taken";
    return next;
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const nextErrors = validate();
    setErrors(nextErrors);
    setFormError(null);
    if (Object.keys(nextErrors).length) return;

    setSubmitting(true);
    try {
      const response = await api.register({
        full_name: form.full_name,
        email: form.email,
        username: form.username.trim().toLowerCase(),
        password: form.password,
        confirm_password: form.confirm_password,
      });
      signIn(response);
      push({
        title: "Account created",
        description: "Let's build your profile.",
        variant: "success",
      });
      navigate("/onboarding", { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        setFormError(error.message);
        if (Object.keys(error.fieldErrors).length) setErrors(error.fieldErrors);
      } else {
        setFormError("Could not create your account. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const availabilityHint = (state: Availability, taken: string, free: string) => {
    if (state.checking) return "Checking availability...";
    if (state.available === true) return free;
    if (state.available === false) return taken;
    return undefined;
  };

  return (
    <AuthLayout
      title="Create your student account"
      subtitle="Free for students. Takes about a minute."
      footer={
        <>
          Already registered?{" "}
          <Link to="/login" className="link font-semibold">
            Sign in instead
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        {formError ? (
          <div className="flex items-start gap-2.5 rounded-xl border border-danger-500/25 bg-danger-50 px-3.5 py-3 animate-fade-in">
            <AlertCircle size={16} className="mt-0.5 shrink-0 text-danger-500" />
            <p className="text-sm text-danger-700">{formError}</p>
          </div>
        ) : null}

        <TextInput
          label="Full name"
          required
          icon={<User size={15} />}
          value={form.full_name}
          autoComplete="name"
          placeholder="Aarav Menon"
          onChange={(event) => update("full_name")(event.target.value)}
          error={errors.full_name}
        />

        <TextInput
          label="Email address"
          required
          type="email"
          icon={<Mail size={15} />}
          value={form.email}
          autoComplete="email"
          placeholder="you@college.edu"
          onChange={(event) => {
            update("email")(event.target.value);
            checkAvailability("email", event.target.value);
          }}
          error={errors.email}
          hint={availabilityHint(emailCheck, "Already registered", "Email is available")}
        />

        <TextInput
          label="Username"
          required
          icon={<AtSign size={15} />}
          value={form.username}
          autoComplete="username"
          placeholder="aarav.menon"
          onChange={(event) => {
            update("username")(event.target.value);
            checkAvailability("username", event.target.value);
          }}
          error={errors.username}
          hint={availabilityHint(usernameCheck, "Already taken", "Username is available")}
        />

        <div>
          <PasswordInput
            id="register-password"
            label="Password"
            value={form.password}
            onChange={update("password")}
            error={errors.password}
            autoComplete="new-password"
          />
          {form.password ? (
            <ul className="mt-2 grid gap-1 sm:grid-cols-3">
              {checks.map((check) => (
                <li
                  key={check.label}
                  className={cn(
                    "flex items-center gap-1.5 text-2xs font-medium transition-colors",
                    check.ok ? "text-brand-700" : "text-ink-400"
                  )}
                >
                  <CheckCircle2 size={12} className={check.ok ? "text-brand-500" : "text-ink-300"} />
                  {check.label}
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        <PasswordInput
          id="register-confirm"
          label="Confirm password"
          value={form.confirm_password}
          onChange={update("confirm_password")}
          error={errors.confirm_password}
          autoComplete="new-password"
        />

        <Button type="submit" size="lg" fullWidth loading={submitting} icon={<ArrowRight size={16} />}>
          {submitting ? "Creating account" : "Create account and start onboarding"}
        </Button>

        <p className="text-center text-2xs leading-relaxed text-ink-400">
          Arjuna AI is student-only in this release. There is no recruiter access, and your profile
          is visible only to you.
        </p>
      </form>
    </AuthLayout>
  );
}
