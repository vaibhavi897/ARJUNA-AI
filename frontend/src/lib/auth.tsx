/**
 * Auth + toast context.
 *
 * The token lives in localStorage only as a session convenience; every piece of
 * student data is fetched from PostgreSQL through the API on demand.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, onUnauthorized, setToken, getToken, type AuthResponse, type User } from "./api";

type AuthState = {
  user: User | null;
  loading: boolean;
  signIn: (response: AuthResponse) => void;
  signOut: (options?: { silent?: boolean }) => Promise<void>;
  refreshUser: () => Promise<User | null>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const signIn = useCallback((response: AuthResponse) => {
    setToken(response.access_token);
    setUser(response.user);
  }, []);

  const signOut = useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) {
      try {
        await api.logout();
      } catch {
        /* the token may already be invalid; sign out locally regardless */
      }
    }
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      return null;
    }
    try {
      const fresh = await api.me();
      setUser(fresh);
      return fresh;
    } catch {
      setToken(null);
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await refreshUser();
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshUser]);

  // A 401 from any request means the session is gone: drop it immediately.
  useEffect(() => onUnauthorized(() => {
    setToken(null);
    setUser(null);
  }), []);

  const value = useMemo(
    () => ({ user, loading, signIn, signOut, refreshUser }),
    [user, loading, signIn, signOut, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

// ---------------------------------------------------------------------------
// Toasts
// ---------------------------------------------------------------------------
export type Toast = {
  id: number;
  title: string;
  description?: string;
  variant: "success" | "error" | "info";
};

type ToastState = {
  toasts: Toast[];
  push: (toast: Omit<Toast, "id">) => void;
  dismiss: (id: number) => void;
};

const ToastContext = createContext<ToastState | null>(null);
let toastId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = ++toastId;
      setToasts((current) => [...current, { ...toast, id }]);
      window.setTimeout(() => dismiss(id), toast.variant === "error" ? 7000 : 4500);
    },
    [dismiss]
  );

  const value = useMemo(() => ({ toasts, push, dismiss }), [toasts, push, dismiss]);
  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast(): ToastState {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside ToastProvider");
  return context;
}
