/** AI Learning Hub shell: one sidebar item, seven internal sections. */
import { NavLink, Outlet } from "react-router-dom";
import { BarChart3, BookMarked, BookOpen, CalendarDays, ClipboardCheck, LayoutDashboard, Youtube } from "lucide-react";
import { AppShell } from "../../components/layout";
import { cn } from "../../lib/utils";

const TABS = [
  { to: "/app/learning", label: "Learning Overview", short: "Overview", icon: <LayoutDashboard size={16} />, end: true },
  { to: "/app/learning/planner", label: "My Learning Planner", short: "Planner", icon: <CalendarDays size={16} /> },
  { to: "/app/learning/materials", label: "Learning Materials", short: "Materials", icon: <BookOpen size={16} /> },
  { to: "/app/learning/youtube", label: "YouTube Summariser", short: "YouTube", icon: <Youtube size={16} /> },
  { to: "/app/learning/notes", label: "My Notes", short: "Notes", icon: <BookMarked size={16} /> },
  { to: "/app/learning/quizzes", label: "Quizzes & Assessments", short: "Quizzes", icon: <ClipboardCheck size={16} /> },
  { to: "/app/learning/progress", label: "Progress & Mastery", short: "Progress", icon: <BarChart3 size={16} /> },
];

export default function LearningLayout() {
  return (
    <AppShell title="AI Learning Hub" subtitle="Plans, notes, videos and quizzes written for you by AI, tracked by real mastery">
      <div className="mx-auto max-w-7xl space-y-5">
        <nav aria-label="Learning Hub sections" className="sticky top-0 z-20 -mx-1 overflow-x-auto rounded-2xl bg-surface-sunken/85 px-1 py-2 backdrop-blur-md [scrollbar-width:none]">
          <ul className="flex min-w-max gap-1.5">
            {TABS.map((t) => (
              <li key={t.to}>
                <NavLink to={t.to} end={t.end} title={t.label}
                  className={({ isActive }) => cn("flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold transition-all", isActive ? "border-forest-800 bg-forest-800 text-white shadow-md" : "border-line-strong bg-white text-ink-600 hover:border-brand-400 hover:text-brand-700")}>
                  {t.icon}<span className="hidden lg:inline">{t.label}</span><span className="lg:hidden">{t.short}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <Outlet />
      </div>
    </AppShell>
  );
}
