/** Shared UI primitives. One file so the design system stays consistent. */
import {
  forwardRef,
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  ChevronDown,
  Info,
  Loader2,
  Plus,
  X,
} from "lucide-react";
import { cn, scoreTone } from "../lib/utils";
import { useToast } from "../lib/auth";

// ---------------------------------------------------------------------------
// Button
// ---------------------------------------------------------------------------
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "outline" | "danger" | "forest";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: ReactNode;
  fullWidth?: boolean;
};

const BUTTON_VARIANTS: Record<string, string> = {
  primary:
    "bg-brand-600 text-white shadow-sm hover:bg-brand-700 active:bg-brand-800 disabled:bg-brand-300",
  forest:
    "bg-forest-800 text-white shadow-sm hover:bg-forest-900 active:bg-forest-900 disabled:bg-forest-400",
  secondary:
    "bg-sage-100 text-forest-800 hover:bg-sage-200 active:bg-sage-300 disabled:text-ink-300",
  outline:
    "border border-line-strong bg-white text-ink-800 hover:border-brand-400 hover:text-brand-700 hover:bg-brand-50/40",
  ghost: "text-ink-600 hover:bg-sage-100 hover:text-forest-800",
  danger: "bg-danger-500 text-white hover:bg-danger-700 disabled:bg-danger-500/50",
};

const BUTTON_SIZES: Record<string, string> = {
  sm: "h-9 px-3 text-sm gap-1.5 rounded-lg",
  md: "h-10 px-4 text-sm gap-2 rounded-xl",
  lg: "h-12 px-6 text-base gap-2 rounded-xl",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, icon, fullWidth, className, children, disabled, ...rest },
  ref
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center font-semibold transition-all duration-200 ease-smooth",
        "disabled:cursor-not-allowed active:scale-[0.98]",
        BUTTON_VARIANTS[variant],
        BUTTON_SIZES[size],
        fullWidth && "w-full",
        className
      )}
      {...rest}
    >
      {loading ? <Loader2 size={16} className="animate-spin" /> : icon}
      {children}
    </button>
  );
});

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------
export function Card({
  children,
  className,
  interactive,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
  as?: any;
}) {
  return (
    <Tag className={cn(interactive ? "card-interactive" : "card", className)}>{children}</Tag>
  );
}

export function SectionHeader({
  title,
  description,
  action,
  icon,
  id,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
  id?: string;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        {icon ? (
          <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-600">
            {icon}
          </span>
        ) : null}
        <div>
          <h2 id={id} className="text-lg font-bold">
            {title}
          </h2>
          {description ? (
            <p className="mt-0.5 max-w-2xl text-sm text-ink-500">{description}</p>
          ) : null}
        </div>
      </div>
      {action}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Badge / Chip
// ---------------------------------------------------------------------------
export function Badge({
  children,
  className,
  tone = "neutral",
}: {
  children: ReactNode;
  className?: string;
  tone?: "neutral" | "brand" | "warn" | "danger" | "info" | "forest";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-sage-100 text-ink-600 border-line",
    brand: "bg-brand-50 text-brand-700 border-brand-200",
    forest: "bg-forest-800 text-white border-forest-800",
    warn: "bg-warn-50 text-warn-700 border-warn-500/25",
    danger: "bg-danger-50 text-danger-700 border-danger-500/20",
    info: "bg-info-50 text-info-700 border-info-500/20",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Form fields
// ---------------------------------------------------------------------------
export function Field({
  label,
  hint,
  error,
  required,
  children,
  htmlFor,
  className,
}: {
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
  htmlFor?: string;
  className?: string;
}) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={htmlFor} className="block text-sm font-semibold text-ink-800">
        {label}
        {required ? <span className="ml-0.5 text-danger-500">*</span> : null}
        {!required ? <span className="ml-1.5 text-xs font-normal text-ink-400">optional</span> : null}
      </label>
      {children}
      {error ? (
        <p className="flex items-start gap-1 text-xs font-medium text-danger-700">
          <AlertCircle size={13} className="mt-0.5 shrink-0" />
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-ink-400">{hint}</p>
      ) : null}
    </div>
  );
}

type TextInputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string;
  icon?: ReactNode;
};

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(function TextInput(
  { label, hint, error, required, icon, className, ...rest },
  ref
) {
  const generatedId = useId();
  const id = rest.id ?? generatedId;
  const input = (
    <div className="relative">
      {icon ? (
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-300">
          {icon}
        </span>
      ) : null}
      <input
        ref={ref}
        id={id}
        aria-invalid={error ? true : undefined}
        className={cn("input-base", error && "input-error", icon && "pl-9", className)}
        {...rest}
      />
    </div>
  );
  if (!label) return input;
  return (
    <Field label={label} hint={hint} error={error} required={required} htmlFor={id}>
      {input}
    </Field>
  );
});

type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  hint?: string;
  error?: string;
};

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea(
  { label, hint, error, required, className, ...rest },
  ref
) {
  const generatedId = useId();
  const id = rest.id ?? generatedId;
  const field = (
    <textarea
      ref={ref}
      id={id}
      className={cn("input-base resize-y min-h-[88px]", error && "input-error", className)}
      {...rest}
    />
  );
  if (!label) return field;
  return (
    <Field label={label} hint={hint} error={error} required={required} htmlFor={id}>
      {field}
    </Field>
  );
});

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  hint?: string;
  error?: string;
  options: { value: string; label: string }[];
};

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, hint, error, required, options, className, ...rest },
  ref
) {
  const generatedId = useId();
  const id = rest.id ?? generatedId;
  const field = (
    <div className="relative">
      <select
        ref={ref}
        id={id}
        className={cn("input-base appearance-none pr-9", error && "input-error", className)}
        {...rest}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown
        size={16}
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-400"
      />
    </div>
  );
  if (!label) return field;
  return (
    <Field label={label} hint={hint} error={error} required={required} htmlFor={id}>
      {field}
    </Field>
  );
});

export function Checkbox({
  checked,
  onChange,
  label,
  description,
  disabled,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: ReactNode;
  description?: ReactNode;
  disabled?: boolean;
}) {
  return (
    <label
      className={cn(
        "flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-white p-3 transition-all duration-200",
        checked ? "border-brand-300 bg-brand-50/50" : "hover:border-line-strong hover:bg-sage-50",
        disabled && "cursor-not-allowed opacity-60"
      )}
    >
      <span
        className={cn(
          "mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md border transition-all duration-200",
          checked ? "border-brand-600 bg-brand-600 text-white" : "border-line-strong bg-white"
        )}
      >
        {checked ? <Check size={13} strokeWidth={3} /> : null}
      </span>
      <input
        type="checkbox"
        className="sr-only"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="min-w-0">
        <span className="block text-sm font-medium text-ink-900">{label}</span>
        {description ? (
          <span className="mt-0.5 block text-xs text-ink-500">{description}</span>
        ) : null}
      </span>
    </label>
  );
}

export function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-ink-900">{label}</p>
        {description ? <p className="mt-0.5 text-xs text-ink-500">{description}</p> : null}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative h-6 w-11 shrink-0 rounded-full transition-colors duration-250",
          checked ? "bg-brand-600" : "bg-sage-300"
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform duration-250 ease-smooth",
            checked ? "translate-x-[22px]" : "translate-x-0.5"
          )}
        />
      </button>
    </div>
  );
}

/** Free-text tag entry: used for technologies, coursework, skills used. */
export function TagInput({
  values,
  onChange,
  placeholder = "Type and press Enter",
  suggestions = [],
  label,
  hint,
  max = 40,
}: {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  suggestions?: string[];
  label?: string;
  hint?: string;
  max?: number;
}) {
  const [draft, setDraft] = useState("");
  const id = useId();

  const add = (raw: string) => {
    const value = raw.trim();
    if (!value) return;
    if (values.some((item) => item.toLowerCase() === value.toLowerCase())) {
      setDraft("");
      return;
    }
    if (values.length >= max) return;
    onChange([...values, value]);
    setDraft("");
  };

  const filtered = draft
    ? suggestions
        .filter(
          (item) =>
            item.toLowerCase().includes(draft.toLowerCase()) &&
            !values.some((value) => value.toLowerCase() === item.toLowerCase())
        )
        .slice(0, 6)
    : [];

  const control = (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {values.map((value) => (
          <span
            key={value}
            className="inline-flex items-center gap-1 rounded-lg bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700 ring-1 ring-brand-100 animate-scale-in"
          >
            {value}
            <button
              type="button"
              onClick={() => onChange(values.filter((item) => item !== value))}
              className="rounded p-0.5 text-brand-500 transition-colors hover:bg-brand-100 hover:text-brand-800"
              aria-label={`Remove ${value}`}
            >
              <X size={12} />
            </button>
          </span>
        ))}
      </div>
      <div className="relative">
        <input
          id={id}
          value={draft}
          placeholder={placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === ",") {
              event.preventDefault();
              add(draft);
            } else if (event.key === "Backspace" && !draft && values.length) {
              onChange(values.slice(0, -1));
            }
          }}
          className="input-base"
        />
        {filtered.length ? (
          <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-xl border border-line bg-white shadow-float animate-fade-in">
            {filtered.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => add(item)}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-ink-700 transition-colors hover:bg-brand-50 hover:text-brand-700"
              >
                <Plus size={13} className="text-brand-500" />
                {item}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );

  if (!label) return control;
  return (
    <Field label={label} hint={hint} htmlFor={id}>
      {control}
    </Field>
  );
}

// ---------------------------------------------------------------------------
// Progress + score indicators
// ---------------------------------------------------------------------------
export function ProgressBar({
  value,
  max = 100,
  tone,
  size = "md",
  showLabel,
  className,
}: {
  value: number;
  max?: number;
  tone?: string;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}) {
  const percent = Math.max(0, Math.min(100, (value / max) * 100));
  const heights = { sm: "h-1.5", md: "h-2.5", lg: "h-3.5" };
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className={cn("relative w-full overflow-hidden rounded-full bg-sage-200", heights[size])}>
        <div
          className="h-full rounded-full transition-[width] duration-700 ease-smooth"
          style={{ width: `${percent}%`, backgroundColor: tone ?? scoreTone(percent) }}
        />
      </div>
      {showLabel ? (
        <span className="w-10 shrink-0 text-right text-xs font-bold tabular-nums text-ink-700">
          {Math.round(value)}
        </span>
      ) : null}
    </div>
  );
}

export function ScoreRing({
  score,
  size = 132,
  label,
  sublabel,
  strokeWidth = 11,
}: {
  score: number;
  size?: number;
  label?: string;
  sublabel?: string;
  strokeWidth?: number;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const [offset, setOffset] = useState(circumference);

  useEffect(() => {
    const frame = requestAnimationFrame(() =>
      setOffset(circumference - (Math.max(0, Math.min(100, score)) / 100) * circumference)
    );
    return () => cancelAnimationFrame(frame);
  }, [score, circumference]);

  return (
    <div className="relative inline-grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#EAF4EC"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={scoreTone(score)}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1.1s cubic-bezier(0.22, 1, 0.36, 1)" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <p
            className="font-display text-3xl font-extrabold leading-none tabular-nums"
            style={{ color: scoreTone(score) }}
          >
            {Math.round(score)}
          </p>
          {label ? <p className="mt-1 text-2xs font-semibold text-ink-400">{label}</p> : null}
          {sublabel ? <p className="text-2xs text-ink-400">{sublabel}</p> : null}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// States
// ---------------------------------------------------------------------------
export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("animate-spin text-brand-500", className)} size={20} />;
}

export function LoadingBlock({ label = "Loading", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div className="space-y-3" role="status" aria-busy="true" aria-label={label}>
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton h-14 w-full" />
      ))}
    </div>
  );
}

export function PageLoader({ label = "Loading your workspace" }: { label?: string }) {
  return (
    <div className="grid min-h-[60vh] place-items-center">
      <div className="text-center">
        <div className="relative mx-auto h-14 w-14">
          <span className="absolute inset-0 rounded-full bg-brand-200 animate-pulse-ring" />
          <span className="absolute inset-0 grid place-items-center rounded-full bg-brand-600 font-display text-lg font-extrabold text-white">
            A
          </span>
        </div>
        <p className="mt-4 text-sm font-medium text-ink-500">{label}...</p>
      </div>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid place-items-center rounded-2xl border border-dashed border-line-strong bg-surface-muted px-6 py-10 text-center",
        className
      )}
    >
      <div className="max-w-sm">
        {icon ? (
          <span className="mx-auto mb-3 grid h-11 w-11 place-items-center rounded-2xl bg-sage-100 text-brand-600">
            {icon}
          </span>
        ) : null}
        <p className="font-semibold text-ink-800">{title}</p>
        {description ? <p className="mt-1 text-sm text-ink-500">{description}</p> : null}
        {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
      </div>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-2xl border border-danger-500/25 bg-danger-50 px-5 py-4">
      <div className="flex items-start gap-3">
        <AlertCircle size={18} className="mt-0.5 shrink-0 text-danger-500" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-danger-700">Something went wrong</p>
          <p className="mt-0.5 break-words text-sm text-danger-700/80">{message}</p>
        </div>
        {onRetry ? (
          <Button size="sm" variant="outline" onClick={onRetry}>
            Retry
          </Button>
        ) : null}
      </div>
    </div>
  );
}

export function InlineNote({
  children,
  tone = "info",
  icon,
}: {
  children: ReactNode;
  tone?: "info" | "warn" | "brand";
  icon?: ReactNode;
}) {
  const tones = {
    info: "border-info-500/20 bg-info-50 text-info-700",
    warn: "border-warn-500/25 bg-warn-50 text-warn-700",
    brand: "border-brand-200 bg-brand-50 text-brand-700",
  };
  return (
    <div className={cn("flex items-start gap-2.5 rounded-xl border px-3.5 py-3 text-sm", tones[tone])}>
      <span className="mt-0.5 shrink-0">{icon ?? <Info size={15} />}</span>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = "lg",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: "md" | "lg" | "xl";
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panelRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [open, onClose]);

  if (!open) return null;

  const widths = { md: "max-w-lg", lg: "max-w-3xl", xl: "max-w-5xl" };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6">
      <div
        className="absolute inset-0 bg-forest-900/45 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden
      />
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          "relative z-10 flex max-h-[92vh] w-full flex-col overflow-hidden rounded-t-3xl bg-white shadow-float animate-fade-up sm:rounded-3xl",
          widths[size]
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4 sm:px-6">
          <div className="min-w-0">
            <h3 className="text-base font-bold">{title}</h3>
            {description ? <p className="mt-0.5 text-sm text-ink-500">{description}</p> : null}
          </div>
          <button
            onClick={onClose}
            className="shrink-0 rounded-lg p-1.5 text-ink-400 transition-colors hover:bg-sage-100 hover:text-ink-700"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">{children}</div>
        {footer ? (
          <div className="border-t border-line bg-surface-muted px-5 py-3.5 sm:px-6">{footer}</div>
        ) : null}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------
export function Tabs({
  tabs,
  active,
  onChange,
  className,
}: {
  tabs: { id: string; label: string; count?: number }[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={cn(
        "no-scrollbar flex gap-1 overflow-x-auto rounded-xl bg-sage-100 p-1",
        className
      )}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            "shrink-0 rounded-lg px-3.5 py-2 text-sm font-semibold transition-all duration-200",
            active === tab.id
              ? "bg-white text-forest-800 shadow-sm"
              : "text-ink-500 hover:text-forest-700"
          )}
        >
          {tab.label}
          {typeof tab.count === "number" ? (
            <span
              className={cn(
                "ml-1.5 rounded-full px-1.5 py-0.5 text-2xs font-bold tabular-nums",
                active === tab.id ? "bg-brand-100 text-brand-700" : "bg-white/70 text-ink-400"
              )}
            >
              {tab.count}
            </span>
          ) : null}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Toaster
// ---------------------------------------------------------------------------
export function Toaster() {
  const { toasts, dismiss } = useToast();
  if (!toasts.length) return null;

  const icons = {
    success: <CheckCircle2 size={17} className="text-brand-600" />,
    error: <AlertCircle size={17} className="text-danger-500" />,
    info: <Info size={17} className="text-info-500" />,
  };
  const borders = {
    success: "border-l-brand-500",
    error: "border-l-danger-500",
    info: "border-l-info-500",
  };

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={cn(
            "pointer-events-auto flex items-start gap-3 rounded-xl border border-l-4 border-line bg-white px-4 py-3 shadow-float animate-slide-in-right",
            borders[toast.variant]
          )}
        >
          <span className="mt-0.5 shrink-0">{icons[toast.variant]}</span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-ink-900">{toast.title}</p>
            {toast.description ? (
              <p className="mt-0.5 break-words text-xs text-ink-500">{toast.description}</p>
            ) : null}
          </div>
          <button
            onClick={() => dismiss(toast.id)}
            className="shrink-0 rounded p-1 text-ink-300 transition-colors hover:bg-sage-100 hover:text-ink-600"
            aria-label="Dismiss"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Repeatable list editor used by several onboarding/settings sections
// ---------------------------------------------------------------------------
export function RepeaterItem({
  index,
  title,
  onRemove,
  children,
  removable = true,
}: {
  index: number;
  title: string;
  onRemove: () => void;
  children: ReactNode;
  removable?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface-muted p-4 animate-fade-up sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-forest-800 text-xs font-bold text-white">
            {index + 1}
          </span>
          <p className="text-sm font-bold text-ink-800">{title}</p>
        </div>
        {removable ? (
          <button
            type="button"
            onClick={onRemove}
            className="rounded-lg px-2 py-1 text-xs font-semibold text-danger-700 transition-colors hover:bg-danger-50"
          >
            Remove
          </button>
        ) : null}
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}
