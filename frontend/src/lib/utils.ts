/** Small shared helpers. */

export function cn(...values: unknown[]): string {
  // Accepts the usual `cond && "class"` shorthand, where cond may be any falsy value.
  return values.filter((value): value is string => typeof value === "string" && value.length > 0).join(" ");
}

export function bandColor(band: string): string {
  switch (band) {
    case "Placement Ready":
      return "text-brand-700 bg-brand-100 border-brand-200";
    case "Strong":
      return "text-brand-600 bg-brand-50 border-brand-100";
    case "Developing":
      return "text-warn-700 bg-warn-50 border-warn-500/20";
    case "Emerging":
      return "text-warn-700 bg-warn-50 border-warn-500/30";
    default:
      return "text-danger-700 bg-danger-50 border-danger-500/20";
  }
}

export function scoreTone(score: number): string {
  if (score >= 80) return "#187C4F";
  if (score >= 65) return "#229A63";
  if (score >= 50) return "#C9872B";
  return "#C0493D";
}

export function priorityStyles(priority: string): string {
  switch (priority) {
    case "high":
      return "bg-danger-50 text-danger-700 border-danger-500/20";
    case "medium":
      return "bg-warn-50 text-warn-700 border-warn-500/25";
    default:
      return "bg-sage-100 text-ink-600 border-line";
  }
}

export function severityStyles(severity: string): string {
  switch (severity) {
    case "high":
      return "border-l-danger-500 bg-danger-50/50";
    case "medium":
      return "border-l-warn-500 bg-warn-50/50";
    default:
      return "border-l-brand-400 bg-brand-50/50";
  }
}

export function gapStatusLabel(status: string): string {
  switch (status) {
    case "missing":
      return "Missing";
    case "claimed_only":
      return "Claimed, not proven";
    case "below_expected":
      return "Below expected level";
    default:
      return "Met";
  }
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function relativeTime(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  const diff = Date.now() - date.getTime();
  const minutes = Math.round(diff / 60000);
  if (Number.isNaN(minutes)) return "-";
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(value);
}

export function titleCase(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function monthsToText(months: number): string {
  if (!months) return "0 months";
  if (months < 12) return `${months} month${months === 1 ? "" : "s"}`;
  const years = Math.floor(months / 12);
  const rest = months % 12;
  return rest ? `${years}y ${rest}m` : `${years} year${years === 1 ? "" : "s"}`;
}

export const PROFICIENCIES = ["beginner", "intermediate", "advanced"] as const;

export const SKILL_CATEGORY_LABELS: Record<string, string> = {
  programming: "Programming",
  data_ai: "Data & AI",
  cloud_devops: "Cloud & DevOps",
  cs_fundamentals: "CS Fundamentals",
  finance: "Finance",
  business: "Business & Strategy",
  tools: "Tools & Platforms",
  soft_skills: "Soft Skills",
  other: "Other",
};

export const EXPERIENCE_TYPE_LABELS: Record<string, string> = {
  internship: "Internship",
  job: "Work experience",
  position_of_responsibility: "Position of responsibility",
  extracurricular: "Extracurricular",
};

export const ACADEMIC_LEVEL_LABELS: Record<string, string> = {
  class_10: "Class 10",
  class_12: "Class 12",
  diploma: "Diploma",
  undergraduate: "Undergraduate",
  postgraduate: "Postgraduate",
  other: "Other",
};

/** Chart palette - sequential greens with two neutral accents for contrast. */
export const CHART_COLORS = [
  "#187C4F",
  "#44B47C",
  "#0C3326",
  "#A8E1C0",
  "#2B6B4E",
  "#73CC9D",
  "#124433",
  "#C9872B",
];
