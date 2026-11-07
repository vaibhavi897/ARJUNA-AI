/** App shell, sidebar, top bar and public navigation. */
import { motion } from "motion/react";
import Assistant from "./Assistant";
import LanguageSwitcher from "./LanguageSwitcher";
import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Mic2,
  LogOut,
  Compass,
  BriefcaseBusiness,
  GraduationCap,
  FileText,
  Menu,
  Settings as SettingsIcon,
  Sparkles,
  X,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { cn } from "../lib/utils";
import { Button } from "./ui";

export function Logo({
  variant = "dark",
  size = "md",
}: {
  variant?: "dark" | "light";
  size?: "sm" | "md" | "lg";
}) {
  const sizes = {
    sm: { box: "h-8 w-8 text-sm", text: "text-base" },
    md: { box: "h-9 w-9 text-base", text: "text-lg" },
    lg: { box: "h-11 w-11 text-lg", text: "text-xl" },
  };
  return (
    <span className="inline-flex items-center gap-2.5">
      <span
        className={cn(
          "relative grid shrink-0 place-items-center rounded-xl font-display font-extrabold",
          sizes[size].box,
          variant === "light" ? "bg-white text-forest-800" : "bg-forest-800 text-white"
        )}
      >
        A
        <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-brand-400 ring-2 ring-white" />
      </span>
      <span
        className={cn(
          "font-display font-extrabold tracking-tight",
          sizes[size].text,
          variant === "light" ? "text-white" : "text-forest-800"
        )}
      >
        Arjuna<span className="text-brand-500"> AI</span>
      </span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------
type NavItem = {
  to: string;
  label: string;
  icon: ReactNode;
  ready: boolean;
};

// Only shipped modules are listed. The placeholder routes still resolve, so a
// teammate can add their entry back here the moment the feature is real.
const NAV_ITEMS: NavItem[] = [
  { to: "/app/dashboard", label: "Student Dashboard", icon: <LayoutDashboard size={18} />, ready: true },
  { to: "/app/interview-arena", label: "Interview Arena", icon: <Mic2 size={18} />, ready: true },
  { to: "/app/learning", label: "AI Learning Hub", icon: <GraduationCap size={18} />, ready: true },
  { to: "/app/resume-builder", label: "Dynamic Resume Builder", icon: <FileText size={18} />, ready: true },
  { to: "/app/careerverse", label: "CareerVerse", icon: <Compass size={18} />, ready: true },
  { to: "/app/career-connect/opportunities", label: "Career Connect", icon: <BriefcaseBusiness size={18} />, ready: true },
  { to: "/app/settings", label: "Settings", icon: <SettingsIcon size={18} />, ready: true },
];

function SidebarContent({
  collapsed,
  onNavigate,
}: {
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col mesh-forest">
      <div className={cn("flex items-center px-4 py-5", collapsed && "justify-center px-2")}>
        <Link to="/app/dashboard" onClick={onNavigate} aria-label="Arjuna AI">
          {collapsed ? (
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-white font-display text-base font-extrabold text-forest-800">
              A
            </span>
          ) : (
            <Logo variant="light" />
          )}
        </Link>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {!collapsed ? (
          <p className="px-2.5 pb-2 pt-1 text-2xs font-semibold uppercase tracking-[0.14em] text-white/40">
            Workspace
          </p>
        ) : null}
        {NAV_ITEMS.map((item) => (
          <div key={item.to}>
            <NavLink
              to={item.to}
              onClick={onNavigate}
              title={collapsed ? item.label : undefined}
              className={({ isActive }) =>
                cn(
                  "group relative flex items-center gap-3 rounded-xl px-2.5 py-2.5 text-sm font-medium transition-all duration-200",
                  collapsed && "justify-center px-2",
                  isActive
                    ? "bg-white/[0.14] text-white shadow-inset"
                    : "text-white/65 hover:bg-white/[0.07] hover:text-white"
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive ? (
                    <span className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-r-full bg-brand-400" />
                  ) : null}
                  <span className="shrink-0">{item.icon}</span>
                  {!collapsed ? (
                    <>
                      <span className="min-w-0 flex-1 truncate">{item.label}</span>
                      {!item.ready ? (
                        <span className="shrink-0 rounded-full bg-white/10 px-1.5 py-0.5 text-2xs font-semibold text-white/55">
                          Soon
                        </span>
                      ) : null}
                    </>
                  ) : null}
                </>
              )}
            </NavLink>
          </div>
        ))}
      </nav>

      <div className="border-t border-white/10 p-3">
        {!collapsed ? (
          <div className="mb-2 flex items-center gap-2.5 rounded-xl bg-white/[0.06] px-2.5 py-2.5">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-400 text-xs font-bold text-forest-900">
              {(user?.full_name ?? "S")
                .split(" ")
                .slice(0, 2)
                .map((part) => part[0])
                .join("")
                .toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-white">{user?.full_name}</p>
              <p className="truncate text-2xs text-white/50">{user?.email}</p>
            </div>
          </div>
        ) : null}
        <button
          onClick={async () => {
            await signOut();
            navigate("/login", { replace: true });
          }}
          title={collapsed ? "Sign out" : undefined}
          className={cn(
            "flex w-full items-center gap-3 rounded-xl px-2.5 py-2.5 text-sm font-medium text-white/60 transition-colors hover:bg-white/[0.07] hover:text-white",
            collapsed && "justify-center px-2"
          )}
        >
          <LogOut size={18} />
          {!collapsed ? "Sign out" : null}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// App shell
// ---------------------------------------------------------------------------
export function AppShell({
  children,
  title,
  subtitle,
  actions,
}: {
  children: ReactNode;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem("arjuna.sidebar") === "collapsed";
    } catch {
      return false;
    }
  });
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setMobileOpen(false), [location.pathname]);

  useEffect(() => {
    try {
      localStorage.setItem("arjuna.sidebar", collapsed ? "collapsed" : "expanded");
    } catch {
      /* preference is cosmetic; ignore storage failures */
    }
  }, [collapsed]);

  return (
    <div className="min-h-screen bg-surface-sunken">
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 hidden transition-[width] duration-300 ease-smooth lg:block",
          collapsed ? "w-[76px]" : "w-[264px]"
        )}
      >
        <SidebarContent collapsed={collapsed} />
        <button
          onClick={() => setCollapsed((value) => !value)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="absolute -right-3 top-20 grid h-6 w-6 place-items-center rounded-full border border-line bg-white text-ink-500 shadow-card transition-colors hover:text-brand-600"
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-forest-900/50 backdrop-blur-sm animate-fade-in"
            onClick={() => setMobileOpen(false)}
            aria-hidden
          />
          <aside className="absolute inset-y-0 left-0 w-[272px] animate-slide-in-right">
            <SidebarContent collapsed={false} onNavigate={() => setMobileOpen(false)} />
            <button
              onClick={() => setMobileOpen(false)}
              className="absolute right-3 top-5 rounded-lg p-1.5 text-white/70 hover:bg-white/10 hover:text-white"
              aria-label="Close navigation"
            >
              <X size={18} />
            </button>
          </aside>
        </div>
      ) : null}

      <div
        className={cn(
          "transition-[padding] duration-300 ease-smooth",
          collapsed ? "lg:pl-[76px]" : "lg:pl-[264px]"
        )}
      >
        <header className="sticky top-0 z-20 border-b border-line bg-white/85 backdrop-blur-md">
          <div className="flex items-center gap-3 px-4 py-3.5 sm:px-6 lg:px-8">
            <button
              onClick={() => setMobileOpen(true)}
              className="rounded-lg p-2 text-ink-600 transition-colors hover:bg-sage-100 lg:hidden"
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-lg font-bold sm:text-xl">{title}</h1>
              {subtitle ? (
                <p className="truncate text-xs text-ink-500 sm:text-sm">{subtitle}</p>
              ) : null}
            </div>
            <div className="flex shrink-0 items-center gap-2"><LanguageSwitcher />{actions}</div>
          </div>
        </header>

        <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <motion.div key={location.pathname} className="mx-auto max-w-[1400px]" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}>{children}</motion.div>
        </main>
        <Assistant />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public chrome
// ---------------------------------------------------------------------------
export function PublicNav() {
  const { user } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const links = [
    { href: "#how-it-works", label: "How it works" },
    { href: "#features", label: "Features" },
    { href: "#domains", label: "Career domains" },
    { href: "#benefits", label: "For students" },
  ];

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-40 transition-all duration-300",
        scrolled ? "border-b border-line bg-white/90 backdrop-blur-md" : "bg-transparent"
      )}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6 lg:px-8">
        <Link to="/" aria-label="Arjuna AI home">
          <Logo />
        </Link>

        <nav className="hidden items-center gap-7 md:flex">
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-ink-600 transition-colors hover:text-forest-800"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2.5 md:flex">
          {user ? (
            <Link to="/app/dashboard">
              <Button size="sm" icon={<LayoutDashboard size={15} />}>
                My dashboard
              </Button>
            </Link>
          ) : (
            <>
              <Link to="/login">
                <Button variant="ghost" size="sm">
                  Log in
                </Button>
              </Link>
              <Link to="/register">
                <Button size="sm" icon={<Sparkles size={15} />}>
                  Register free
                </Button>
              </Link>
            </>
          )}
        </div>

        <button
          onClick={() => setOpen((value) => !value)}
          className="rounded-lg p-2 text-ink-700 transition-colors hover:bg-sage-100 md:hidden"
          aria-label="Toggle menu"
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {open ? (
        <div className="border-t border-line bg-white px-4 py-3 md:hidden animate-fade-in">
          <nav className="flex flex-col">
            {links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-2 py-2.5 text-sm font-medium text-ink-700 hover:bg-sage-50"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="mt-3 flex gap-2">
            {user ? (
              <Link to="/app/dashboard" className="flex-1">
                <Button fullWidth>My dashboard</Button>
              </Link>
            ) : (
              <>
                <Link to="/login" className="flex-1">
                  <Button variant="outline" fullWidth>
                    Log in
                  </Button>
                </Link>
                <Link to="/register" className="flex-1">
                  <Button fullWidth>Register</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      ) : null}
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer className="mesh-forest text-white/70">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-4 lg:px-8">
        <div className="lg:col-span-2">
          <Logo variant="light" />
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/60">
            Arjuna AI scores a student's readiness for specific placement roles, explains every
            point, and turns the gaps into a plan. Built for students first.
          </p>
        </div>

        <div>
          <p className="mb-3 text-2xs font-semibold uppercase tracking-[0.14em] text-white/40">
            Platform
          </p>
          <ul className="space-y-2 text-sm">
            <li>
              <a href="#how-it-works" className="transition-colors hover:text-white">
                How it works
              </a>
            </li>
            <li>
              <a href="#features" className="transition-colors hover:text-white">
                Features
              </a>
            </li>
            <li>
              <a href="#domains" className="transition-colors hover:text-white">
                Career domains
              </a>
            </li>
            <li>
              <a href="#benefits" className="transition-colors hover:text-white">
                For students
              </a>
            </li>
          </ul>
        </div>

        <div>
          <p className="mb-3 text-2xs font-semibold uppercase tracking-[0.14em] text-white/40">
            Get started
          </p>
          <ul className="space-y-2 text-sm">
            <li>
              <Link to="/register" className="transition-colors hover:text-white">
                Create a student account
              </Link>
            </li>
            <li>
              <Link to="/login" className="transition-colors hover:text-white">
                Log in
              </Link>
            </li>
            <li>
              <a href="/docs" className="transition-colors hover:text-white">
                API documentation
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-5 text-xs text-white/45 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <p>© {new Date().getFullYear()} Arjuna AI. Student career readiness platform.</p>
          <p>Phase 1 - student experience. Recruiter tools are not part of this release.</p>
        </div>
      </div>
    </footer>
  );
}
