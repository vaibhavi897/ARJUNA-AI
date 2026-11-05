/**
 * The onboarding career companion.
 *
 * An illustrated mentor that stays consistent across every step, reacts to the
 * current step and to completion, and explains why each piece of information is
 * being collected. The illustration is inline SVG so it never 404s and inherits
 * the brand palette.
 */
import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Lightbulb, MessageSquareQuote, Sparkles } from "lucide-react";
import { cn } from "../lib/utils";
import { ProgressBar } from "./ui";

/** Consistent illustrated mentor: same character, two expressions. */
function MentorIllustration({ celebrating }: { celebrating: boolean }) {
  return (
    <svg
      viewBox="0 0 120 120"
      className={cn("h-full w-full", celebrating && "animate-float")}
      role="img"
      aria-label="Arjuna AI career mentor"
    >
      <defs>
        <linearGradient id="mentorBg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#D3F0DE" />
          <stop offset="100%" stopColor="#A8E1C0" />
        </linearGradient>
        <linearGradient id="mentorShirt" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1B5740" />
          <stop offset="100%" stopColor="#0C3326" />
        </linearGradient>
      </defs>

      <circle cx="60" cy="60" r="56" fill="url(#mentorBg)" />
      <circle cx="60" cy="60" r="56" fill="none" stroke="#73CC9D" strokeWidth="1.5" opacity="0.5" />

      {/* shoulders */}
      <path d="M26 112c0-19 15-30 34-30s34 11 34 30z" fill="url(#mentorShirt)" />
      {/* collar */}
      <path d="M49 84l11 11 11-11-5-4-6 5-6-5z" fill="#F5FAF6" opacity="0.92" />
      {/* neck */}
      <rect x="54" y="70" width="12" height="14" rx="6" fill="#D9A47A" />
      {/* head */}
      <ellipse cx="60" cy="52" rx="20" ry="22" fill="#E8B88E" />
      {/* hair */}
      <path
        d="M39 48c0-13 9-23 21-23s21 10 21 23c0-6-9-9-21-9s-21 3-21 9z"
        fill="#2C2117"
      />
      <path d="M39 48c-1 6 0 10 1 12 1-6 1-10 0-12z" fill="#2C2117" />
      <path d="M81 48c1 6 0 10-1 12-1-6-1-10 0-12z" fill="#2C2117" />
      {/* ears */}
      <circle cx="39" cy="54" r="3.5" fill="#D9A47A" />
      <circle cx="81" cy="54" r="3.5" fill="#D9A47A" />
      {/* eyes */}
      {celebrating ? (
        <>
          <path d="M48 50q4-4 8 0" stroke="#2C2117" strokeWidth="2.2" fill="none" strokeLinecap="round" />
          <path d="M64 50q4-4 8 0" stroke="#2C2117" strokeWidth="2.2" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          <ellipse cx="52" cy="51" rx="2.6" ry="3" fill="#2C2117" />
          <ellipse cx="68" cy="51" rx="2.6" ry="3" fill="#2C2117" />
          <circle cx="52.9" cy="50.2" r="0.9" fill="#FFFFFF" />
          <circle cx="68.9" cy="50.2" r="0.9" fill="#FFFFFF" />
        </>
      )}
      {/* brows */}
      <path d="M47 44.5q5-2.5 10 0" stroke="#2C2117" strokeWidth="1.8" fill="none" strokeLinecap="round" />
      <path d="M63 44.5q5-2.5 10 0" stroke="#2C2117" strokeWidth="1.8" fill="none" strokeLinecap="round" />
      {/* mouth */}
      {celebrating ? (
        <path d="M53 60q7 7 14 0" stroke="#8A4B3A" strokeWidth="2.2" fill="none" strokeLinecap="round" />
      ) : (
        <path d="M54 60q6 4 12 0" stroke="#8A4B3A" strokeWidth="2" fill="none" strokeLinecap="round" />
      )}
      {/* badge */}
      <circle cx="78" cy="98" r="9" fill="#44B47C" />
      <path
        d="M74 98l3 3 6-6"
        stroke="#07251B"
        strokeWidth="2.2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Companion({
  message,
  stepTitle,
  stepNumber,
  totalSteps,
  percent,
  celebrating = false,
  why,
  className,
}: {
  message: string;
  stepTitle: string;
  stepNumber: number;
  totalSteps: number;
  percent: number;
  celebrating?: boolean;
  why?: string[];
  className?: string;
}) {
  const [typed, setTyped] = useState(message);
  const previous = useRef(message);

  // Soft fade when the message changes, so it feels like the mentor is talking.
  useEffect(() => {
    if (previous.current === message) return;
    previous.current = message;
    setTyped("");
    const timer = window.setTimeout(() => setTyped(message), 140);
    return () => window.clearTimeout(timer);
  }, [message]);

  return (
    <aside className={cn("space-y-4", className)}>
      <div className="relative overflow-hidden rounded-2xl mesh-forest p-5 text-white shadow-card">
        <div className="absolute inset-0 grid-lines opacity-[0.06]" aria-hidden />

        <div className="relative flex items-start gap-3.5">
          <div className="relative h-16 w-16 shrink-0">
            <MentorIllustration celebrating={celebrating} />
            <span className="absolute -right-0.5 -top-0.5 grid h-5 w-5 place-items-center rounded-full bg-brand-400 text-forest-900 ring-2 ring-forest-800">
              {celebrating ? <CheckCircle2 size={12} /> : <Sparkles size={11} />}
            </span>
          </div>
          <div className="min-w-0 pt-0.5">
            <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-brand-300">
              Your career mentor
            </p>
            <p className="font-display text-base font-bold">Arjun</p>
            <p className="text-2xs text-white/50">
              Step {stepNumber} of {totalSteps} · {stepTitle}
            </p>
          </div>
        </div>

        {/* Speech bubble */}
        <div className="relative mt-4">
          <span
            className="absolute -top-1.5 left-7 h-3 w-3 rotate-45 bg-white/[0.11]"
            aria-hidden
          />
          <div className="relative min-h-[72px] rounded-xl bg-white/[0.11] p-3.5 ring-1 ring-white/10">
            <MessageSquareQuote size={13} className="mb-1.5 text-brand-300" />
            <p
              key={typed}
              className="text-sm leading-relaxed text-white/90 animate-fade-in"
              aria-live="polite"
            >
              {typed}
            </p>
          </div>
        </div>

        <div className="relative mt-4">
          <div className="mb-1.5 flex items-center justify-between text-2xs font-semibold text-white/55">
            <span>Onboarding progress</span>
            <span className="tabular-nums text-brand-300">{percent}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-brand-400 transition-[width] duration-700 ease-smooth"
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
      </div>

      {why?.length ? (
        <div className="rounded-2xl border border-line bg-surface-muted p-4">
          <p className="flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-[0.14em] text-ink-400">
            <Lightbulb size={12} className="text-warn-500" />
            Why this matters
          </p>
          <ul className="mt-2.5 space-y-2">
            {why.map((item) => (
              <li key={item} className="flex items-start gap-2 text-xs leading-relaxed text-ink-600">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-400" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </aside>
  );
}

/** Horizontal step rail shown above the form. */
export function StepRail({
  steps,
  current,
  onSelect,
}: {
  steps: { step: number; title: string; is_complete: boolean; is_optional: boolean }[];
  current: number;
  onSelect: (step: number) => void;
}) {
  return (
    <div className="no-scrollbar -mx-1 overflow-x-auto px-1 pb-1">
      <ol className="flex min-w-max items-center gap-1.5">
        {steps.map((step, index) => {
          const active = step.step === current;
          return (
            <li key={step.step} className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => onSelect(step.step)}
                aria-current={active ? "step" : undefined}
                className={cn(
                  "group flex items-center gap-2 rounded-xl border px-2.5 py-2 text-left transition-all duration-200",
                  active
                    ? "border-brand-300 bg-brand-50 shadow-sm"
                    : step.is_complete
                      ? "border-line bg-white hover:border-brand-200"
                      : "border-dashed border-line bg-surface-muted hover:border-line-strong"
                )}
              >
                <span
                  className={cn(
                    "grid h-6 w-6 shrink-0 place-items-center rounded-lg text-2xs font-bold transition-colors",
                    step.is_complete
                      ? "bg-brand-600 text-white"
                      : active
                        ? "bg-forest-800 text-white"
                        : "bg-sage-200 text-ink-500"
                  )}
                >
                  {step.is_complete ? <CheckCircle2 size={13} /> : step.step}
                </span>
                <span className="hidden sm:block">
                  <span
                    className={cn(
                      "block whitespace-nowrap text-xs font-semibold",
                      active ? "text-forest-800" : "text-ink-600"
                    )}
                  >
                    {step.title}
                  </span>
                  {step.is_optional ? (
                    <span className="block text-2xs text-ink-400">optional</span>
                  ) : null}
                </span>
              </button>
              {index < steps.length - 1 ? (
                <span
                  className={cn(
                    "h-0.5 w-4 rounded-full",
                    step.is_complete ? "bg-brand-300" : "bg-sage-200"
                  )}
                  aria-hidden
                />
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function MobileProgress({ percent, label }: { percent: number; label: string }) {
  return (
    <div className="lg:hidden">
      <div className="mb-1.5 flex items-center justify-between text-xs font-medium text-ink-500">
        <span>{label}</span>
        <span className="tabular-nums">{percent}%</span>
      </div>
      <ProgressBar value={percent} size="sm" tone="#187C4F" />
    </div>
  );
}
