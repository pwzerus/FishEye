import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeUser, nav, renderApp, router } from "@/test-utils";

vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return {
    ...actual,
    getMe: vi.fn(),
    getProviders: vi.fn(),
    requestPasswordReset: vi.fn(),
    checkPasswordReset: vi.fn(),
    confirmPasswordReset: vi.fn(),
  };
});
const session = await import("@/lib/api/session");
const { ApiError } = await import("@/lib/api/client");
const { ForgotPassword } = await import("./ForgotPassword");
const { ResetPassword } = await import("./ResetPassword");
const { LoginForm } = await import("./LoginForm");

beforeEach(() => {
  vi.mocked(session.getMe).mockResolvedValue(null);
  vi.mocked(session.getProviders).mockResolvedValue({ password: true, google: false, email_ready: true });
  vi.mocked(session.requestPasswordReset).mockReset();
  vi.mocked(session.confirmPasswordReset).mockReset();
  router.replace.mockReset();
  nav.search = new URLSearchParams();
});

describe("the sign-in form", () => {
  it("links to it when signing in, not when signing up", async () => {
    renderApp(<LoginForm />);
    expect(await screen.findByRole("link", { name: "Forgot password?" })).toHaveAttribute("href", "/forgot-password");
    fireEvent.click(screen.getAllByRole("tab")[1]);
    expect(screen.queryByRole("link", { name: "Forgot password?" })).not.toBeInTheDocument();
  });
});

describe("ForgotPassword", () => {
  it("sends the address and says the same thing either way", async () => {
    vi.mocked(session.requestPasswordReset).mockResolvedValue(undefined);
    renderApp(<ForgotPassword />);
    const send = await screen.findByRole("button", { name: "Send reset link" });
    expect(send).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "  me@example.com " } });
    fireEvent.click(send);
    expect(await screen.findByText("Check your email")).toBeInTheDocument();
    expect(session.requestPasswordReset).toHaveBeenCalledWith("me@example.com");
    expect(screen.getByText(/If me@example.com has a FishEye account/)).toBeInTheDocument();
  });

  it("says who to ask when the server can't send mail", async () => {
    vi.mocked(session.getProviders).mockResolvedValue({ password: true, google: false, email_ready: false });
    renderApp(<ForgotPassword />);
    expect(await screen.findByText(/can't send email yet/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send reset link" })).not.toBeInTheDocument();
  });

  it("shows a refusal", async () => {
    vi.mocked(session.requestPasswordReset).mockRejectedValue(new ApiError("Too many attempts.", 429));
    renderApp(<ForgotPassword />);
    fireEvent.change(await screen.findByLabelText("Email"), { target: { value: "me@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many attempts.");
  });
});

describe("ResetPassword", () => {
  it("has nothing to do without a code", async () => {
    renderApp(<ResetPassword />);
    expect(await screen.findByText("That link didn't work")).toBeInTheDocument();
    expect(session.checkPasswordReset).not.toHaveBeenCalled();
  });

  it("says when the link is no good, before anyone types", async () => {
    nav.search = new URLSearchParams("token=old");
    vi.mocked(session.checkPasswordReset).mockResolvedValue({ valid: false, email: null });
    renderApp(<ResetPassword />);
    expect(await screen.findByRole("alert")).toHaveTextContent("expired");
    expect(screen.getByRole("link", { name: "Send reset link" })).toHaveAttribute("href", "/forgot-password");
  });

  it("saves, signs in and goes home", async () => {
    nav.search = new URLSearchParams("token=good");
    vi.mocked(session.checkPasswordReset).mockResolvedValue({ valid: true, email: "me@example.com" });
    vi.mocked(session.confirmPasswordReset).mockResolvedValue(makeUser());
    renderApp(<ResetPassword />);
    const input = await screen.findByLabelText("New password");
    expect(screen.getByText(/For me@example.com/)).toBeInTheDocument();
    const save = screen.getByRole("button", { name: "Save new password" });
    fireEvent.change(input, { target: { value: "short" } });
    expect(save).toBeDisabled();
    fireEvent.change(input, { target: { value: "a long enough one" } });
    fireEvent.click(save);
    await waitFor(() => expect(session.confirmPasswordReset).toHaveBeenCalledWith("good", "a long enough one"));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/"));
  });

  it("keeps the form for a weak password, and drops it for a dead link", async () => {
    nav.search = new URLSearchParams("token=good");
    vi.mocked(session.checkPasswordReset).mockResolvedValue({ valid: true, email: "me@example.com" });
    vi.mocked(session.confirmPasswordReset).mockRejectedValueOnce(new ApiError("That password is too common.", 422));
    renderApp(<ResetPassword />);
    fireEvent.change(await screen.findByLabelText("New password"), { target: { value: "password" } });
    fireEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("too common");
    vi.mocked(session.confirmPasswordReset).mockRejectedValueOnce(new ApiError("expired", 400));
    fireEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect(await screen.findByText("That link didn't work")).toBeInTheDocument();
  });
});
