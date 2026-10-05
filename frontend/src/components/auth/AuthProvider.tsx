"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { getMe, logout as apiLogout } from "@/lib/api/session";
import type { User } from "@/lib/api/types";

/**
 * Who is signed in, for every client component.
 *
 * `loading` is true until the first /api/auth/me answer, so the header can
 * reserve space instead of flashing "Sign in" at a signed-in user.
 * `offline` means the backend couldn't be reached at all — distinct from
 * "signed out", which is a real answer.
 */
interface AuthState {
  user: User | null;
  loading: boolean;
  offline: boolean;
  setUser: (user: User | null) => void;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setUser(await getMe());
      setOffline(false);
    } catch {
      setUser(null);
      setOffline(true);
    } finally {
      setLoading(false);
    }
  }, []);

  // First load: state is only set from the promise callbacks.
  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((u) => {
        if (cancelled) return;
        setUser(u);
        setOffline(false);
      })
      .catch(() => {
        if (cancelled) return;
        setUser(null);
        setOffline(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signOut = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, offline, setUser, refresh, signOut }),
    [user, loading, offline, refresh, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
