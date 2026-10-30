import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeUser, nav, renderApp } from "@/test-utils";

// vi.mock is hoisted above imports, so the factory imports what it needs itself.
vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, getMe: vi.fn(), confirmEmail: vi.fn(), sendVerificationEmail: vi.fn(), listPins: vi.fn(), getProviders: vi.fn() };
});
const session = await import("@/lib/api/session");
const { ApiError } = await import("@/lib/api/client");
const { VerifyEmail } = await import("./VerifyEmail");
const { AccountView } = await import("./AccountView");

beforeEach(() => {
  vi.mocked(session.getMe).mockResolvedValue(null);
  vi.mocked(session.confirmEmail).mockReset();
  vi.mocked(session.sendVerificationEmail).mockReset();
  vi.mocked(session.listPins).mockResolvedValue([]);
  vi.mocked(session.getProviders).mockResolvedValue({ password: true, google: false });
  nav.pathname = "/verify-email";
  nav.search = new URLSearchParams();
});

describe("VerifyEmail", () => {
  it("confirms the address from the link, once", async () => {
    nav.search = new URLSearchParams("token=abc123");
    vi.mocked(session.confirmEmail).mockResolvedValue({ verified: true, email: "amy@example.com" });
    renderApp(<VerifyEmail />);
    expect(await screen.findByRole("heading", { name: "Email confirmed" })).toBeInTheDocument();
    expect(screen.getByText(/amy@example.com is confirmed/)).toBeInTheDocument();
    expect(session.confirmEmail).toHaveBeenCalledTimes(1);
    expect(session.confirmEmail).toHaveBeenCalledWith("abc123");
  });

  it("says why a link failed and how to get a new one", async () => {
    nav.search = new URLSearchParams("token=old");
    vi.mocked(session.confirmEmail).mockRejectedValue(new ApiError("This link has expired. Send a new one from your account page.", 400));
    renderApp(<VerifyEmail />);
    expect(await screen.findByRole("alert")).toHaveTextContent("expired");
    expect(screen.getByRole("link", { name: "Sign in to send a new link" })).toHaveAttribute("href", "/login?next=/account");
  });

  it("doesn't call the server for a link without its code", async () => {
    renderApp(<VerifyEmail />);
    expect(await screen.findByRole("alert")).toHaveTextContent("missing its code");
    expect(session.confirmEmail).not.toHaveBeenCalled();
  });
});

describe("AccountView", () => {
  it("asks an unconfirmed account to confirm, and sends a new link", async () => {
    nav.pathname = "/account";
    vi.mocked(session.getMe).mockResolvedValue(makeUser({ verification_required: true }));
    vi.mocked(session.sendVerificationEmail).mockResolvedValue(makeUser({ verification_required: true }));
    renderApp(<AccountView />);
    expect(await screen.findByText("Confirm your email address")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Send a new link" }));
    await waitFor(() => expect(session.sendVerificationEmail).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("New link sent")).toBeInTheDocument();
  });

  it("shows nothing about it once confirmed or while it is off", async () => {
    nav.pathname = "/account";
    vi.mocked(session.getMe).mockResolvedValue(makeUser());
    renderApp(<AccountView />);
    expect(await screen.findByRole("heading", { name: "Angler Amy" })).toBeInTheDocument();
    expect(screen.queryByText("Confirm your email address")).not.toBeInTheDocument();
  });
});
