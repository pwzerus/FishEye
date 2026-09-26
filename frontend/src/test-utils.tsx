import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

import { AuthProvider } from "@/components/auth/AuthProvider";
import { ToastProvider } from "@/components/ui/Toast";
import type { User } from "@/lib/api/types";

export const router = { push: vi.fn(), replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() };
export const nav = { pathname: "/", search: new URLSearchParams() };

/** For vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock()). */
export const navigationMock = () => ({
  useRouter: () => router,
  usePathname: () => nav.pathname,
  useSearchParams: () => nav.search,
});

export function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    email: "amy@example.com",
    display_name: "Angler Amy",
    role: "user",
    status: "active",
    has_password: true,
    google_connected: false,
    created_at: "2026-09-25T12:00:00Z",
    ...overrides,
  };
}

/** Renders inside the app's providers; getMe must be mocked by the caller. */
export function renderApp(ui: ReactElement) {
  return render(
    <AuthProvider>
      <ToastProvider>{ui}</ToastProvider>
    </AuthProvider>,
  );
}
