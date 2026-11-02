import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeUser, nav, renderApp } from "@/test-utils";

vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, getMe: vi.fn(), sendFeedback: vi.fn() };
});
const session = await import("@/lib/api/session");
const { ApiError } = await import("@/lib/api/client");
const { FeedbackButton } = await import("./FeedbackDialog");

beforeEach(() => {
  vi.mocked(session.sendFeedback).mockReset();
  nav.pathname = "/map";
});

async function open() {
  renderApp(<FeedbackButton label="Send feedback" />);
  await waitFor(() => expect(session.getMe).toHaveBeenCalled());
  fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));
}

describe("Send feedback", () => {
  it("asks to sign in first, and says who to write to if you can't", async () => {
    vi.mocked(session.getMe).mockResolvedValue(null);
    await open();
    expect(await screen.findByText(/Sign in to send feedback/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in", hidden: true })).toHaveAttribute("href", "/login?next=%2Fmap");
    expect(screen.queryByRole("textbox", { hidden: true })).not.toBeInTheDocument();
  });

  it("is one box and one button, sent from the account with the page", async () => {
    vi.mocked(session.getMe).mockResolvedValue(makeUser({ email: "me@example.com" }));
    vi.mocked(session.sendFeedback).mockResolvedValue({ id: 1 });
    await open();
    const box = await screen.findByRole("textbox", { hidden: true });
    expect(screen.getByText(/me@example.com/)).toBeInTheDocument();
    const send = screen.getByRole("button", { name: "Send", hidden: true });
    expect(send).toBeDisabled();
    fireEvent.change(box, { target: { value: "   " } });
    expect(send).toBeDisabled();
    fireEvent.change(box, { target: { value: " The map is slow " } });
    fireEvent.click(send);
    await waitFor(() => expect(session.sendFeedback).toHaveBeenCalledWith("The map is slow", "/map", "en"));
    await waitFor(() => expect(screen.queryByRole("textbox", { hidden: true })).not.toBeInTheDocument());
    expect(await screen.findByText(/We read every message/)).toBeInTheDocument();
  });

  it("keeps what was typed when sending fails", async () => {
    vi.mocked(session.getMe).mockResolvedValue(makeUser());
    vi.mocked(session.sendFeedback).mockRejectedValue(new ApiError("You've sent a lot today.", 429));
    await open();
    fireEvent.change(await screen.findByRole("textbox", { hidden: true }), { target: { value: "Hello there" } });
    fireEvent.click(screen.getByRole("button", { name: "Send", hidden: true }));
    expect(await screen.findByRole("alert", { hidden: true })).toHaveTextContent("You've sent a lot today.");
    expect(screen.getByRole("textbox", { hidden: true })).toHaveValue("Hello there");
  });
});
