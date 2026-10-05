import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeUser, nav, renderApp, router } from "@/test-utils";

// vi.mock is hoisted above imports, so the factory imports what it needs itself.
vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return {
    ...actual,
    getMe: vi.fn(),
    getProviders: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  };
});
const session = await import("@/lib/api/session");
const { ApiError } = await import("@/lib/api/client");
const { LoginForm, safeNext } = await import("./LoginForm");
const { AccountMenu, initials } = await import("./AccountMenu");

beforeEach(() => {
  vi.mocked(session.getMe).mockResolvedValue(null);
  vi.mocked(session.getProviders).mockResolvedValue({ password: true, google: false });
  router.push.mockReset();
  router.replace.mockReset();
  nav.pathname = "/";
  nav.search = new URLSearchParams();
});

describe("helpers", () => {
  it.each([
    ["Angler Amy", "AA"],
    ["Yifei (admin)", "Y"],
    ["bob", "B"],
    ["  ", "?"],
    ["Émile Zola", "ÉZ"],
  ])("initials(%j) = %j", (name, out) => {
    expect(initials(name)).toBe(out);
  });

  it.each([
    [null, "/"],
    ["/community", "/community"],
    ["https://evil.example", "/"],
    ["//evil.example", "/"],
    ["/\\evil", "/"],
    ["/login?next=/x", "/"],
    ["/map?addPin=1", "/map?addPin=1"],
  ])("safeNext(%j) = %j", (raw, out) => {
    expect(safeNext(raw)).toBe(out);
  });
});

describe("LoginForm", () => {
  it("creates an account and goes where the user was headed", async () => {
    nav.search = new URLSearchParams("mode=signup&next=/map?addPin=1");
    vi.mocked(session.register).mockResolvedValue(makeUser());
    renderApp(<LoginForm />);
    fireEvent.change(screen.getByPlaceholderText("What other anglers see"), { target: { value: "Angler Amy" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "amy@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "tight-lines-42" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() => expect(session.register).toHaveBeenCalledWith("amy@example.com", "tight-lines-42", "Angler Amy"));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/map?addPin=1"));
  });

  it("shows the server's message when sign-in fails", async () => {
    vi.mocked(session.login).mockRejectedValue(new ApiError("Email or password is incorrect.", 401));
    renderApp(<LoginForm />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "amy@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "nope-nope" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("explains a Google callback error from the URL", async () => {
    nav.search = new URLSearchParams("error=google_email_exists");
    renderApp(<LoginForm />);
    expect(screen.getByRole("alert")).toHaveTextContent(/connect Google from your account page/);
  });

  it("offers Google only when the server has it configured", async () => {
    renderApp(<LoginForm />);
    await waitFor(() => expect(session.getProviders).toHaveBeenCalled());
    expect(screen.queryByText("Continue with Google")).not.toBeInTheDocument();

    vi.mocked(session.getProviders).mockResolvedValue({ password: true, google: true });
    renderApp(<LoginForm />);
    const link = await screen.findByText("Continue with Google");
    expect(link.closest("a")?.getAttribute("href")).toContain("/api/auth/google/start?next=%2F");
  });

  it("toggles password visibility", () => {
    renderApp(<LoginForm />);
    const input = screen.getByLabelText("Password");
    expect(input).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByLabelText("Show password"));
    expect(input).toHaveAttribute("type", "text");
  });
});

describe("AccountMenu", () => {
  it("links to sign-in with the current page as the return path", async () => {
    nav.pathname = "/community";
    renderApp(<AccountMenu />);
    const link = await screen.findByText("Sign in");
    expect(link.closest("a")).toHaveAttribute("href", "/login?next=%2Fcommunity");
  });

  it("shows admin links only to admins and signs out", async () => {
    vi.mocked(session.getMe).mockResolvedValue(makeUser({ role: "admin" }));
    vi.mocked(session.logout).mockResolvedValue(undefined);
    renderApp(<AccountMenu />);
    fireEvent.click(await screen.findByLabelText("Account menu for Angler Amy"));
    expect(screen.getByRole("menuitem", { name: "Admin" })).toHaveAttribute("href", "/admin");
    fireEvent.click(screen.getByRole("menuitem", { name: "Sign out" }));
    await waitFor(() => expect(session.logout).toHaveBeenCalled());
    expect(await screen.findByText("Sign in")).toBeInTheDocument();
  });

  it("hides the admin link from regular users", async () => {
    vi.mocked(session.getMe).mockResolvedValue(makeUser());
    renderApp(<AccountMenu />);
    fireEvent.click(await screen.findByLabelText("Account menu for Angler Amy"));
    expect(screen.queryByRole("menuitem", { name: "Admin" })).not.toBeInTheDocument();
  });
});
