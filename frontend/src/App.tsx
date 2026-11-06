/** Routing and route guards. */
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, ToastProvider, useAuth } from "./lib/auth";
import { PageLoader, Toaster } from "./components/ui";
import Landing from "./pages/Landing";
import { Login, Register } from "./pages/Auth";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import {
  AIAssessment,
  CareerPaths,
  MyProgress,
  PlacementPrep,
  ResumeBuilder,
} from "./pages/Placeholders";

/** Requires a session. Unfinished onboarding is redirected to the wizard. */
function Protected({
  children,
  requireOnboarding = true,
}: {
  children: React.ReactNode;
  requireOnboarding?: boolean;
}) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <PageLoader label="Checking your session" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (requireOnboarding && !user.onboarding_completed) {
    return <Navigate to="/onboarding" replace />;
  }
  return <>{children}</>;
}

function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center bg-surface-sunken px-4">
      <div className="text-center">
        <p className="font-display text-6xl font-extrabold text-sage-300">404</p>
        <h1 className="mt-3 text-xl font-bold">Page not found</h1>
        <p className="mt-1.5 text-sm text-ink-500">
          That route does not exist in Arjuna AI.
        </p>
        <a
          href="/"
          className="mt-5 inline-block rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
        >
          Back to home
        </a>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Routes>
          {/* Login is the app's startup screen. Keep the public landing page at
              /welcome for visitors who want product information first. */}
          <Route path="/" element={<Login />} />
          <Route path="/welcome" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* onboarding: signed in, completion not required */}
          <Route
            path="/onboarding"
            element={
              <Protected requireOnboarding={false}>
                <Onboarding />
              </Protected>
            }
          />

          {/* app */}
          <Route path="/app" element={<Navigate to="/app/dashboard" replace />} />
          <Route
            path="/app/dashboard"
            element={
              <Protected>
                <Dashboard />
              </Protected>
            }
          />
          <Route
            path="/app/placement-prep"
            element={
              <Protected>
                <PlacementPrep />
              </Protected>
            }
          />
          <Route
            path="/app/resume-builder"
            element={
              <Protected>
                <ResumeBuilder />
              </Protected>
            }
          />
          <Route
            path="/app/ai-assessment"
            element={
              <Protected>
                <AIAssessment />
              </Protected>
            }
          />
          <Route
            path="/app/career-paths"
            element={
              <Protected>
                <CareerPaths />
              </Protected>
            }
          />
          <Route
            path="/app/my-progress"
            element={
              <Protected>
                <MyProgress />
              </Protected>
            }
          />
          <Route
            path="/app/settings"
            element={
              <Protected requireOnboarding={false}>
                <Settings />
              </Protected>
            }
          />

          <Route path="*" element={<NotFound />} />
        </Routes>
        <Toaster />
      </AuthProvider>
    </ToastProvider>
  );
}
