import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, getLakeReportOptions: vi.fn(), reportLake: vi.fn() };
});
const session = await import("@/lib/api/session");
const { LakeReportDialog } = await import("./LakeReportDialog");

const REASONS = [
  { id: "not_public", label: "It isn't open to the public" },
  { id: "other", label: "Something else" },
];

beforeEach(() => {
  vi.mocked(session.getLakeReportOptions).mockResolvedValue({ reasons: REASONS });
  vi.mocked(session.reportLake).mockReset().mockResolvedValue({ received: true, id: 1 });
});

describe("LakeReportDialog", () => {
  it("sends what's wrong with a lake", async () => {
    const onSent = vi.fn();
    const onClose = vi.fn();
    render(<LakeReportDialog target={{ kind: "problem", lakeId: 9, lakeName: "Lake Fork" }} open onClose={onClose} onSent={onSent} />);
    expect(screen.getByRole("dialog", { name: "Something wrong with Lake Fork?" })).toBeInTheDocument();
    const send = screen.getByRole("button", { name: "Send" });
    expect(send).toBeDisabled();
    fireEvent.click(await screen.findByRole("radio", { name: "Something else" }));
    expect(send).toBeDisabled(); // "something else" needs a word on what
    fireEvent.change(screen.getByLabelText("Details"), { target: { value: "  Gate is locked  " } });
    fireEvent.click(send);
    await waitFor(() =>
      expect(session.reportLake).toHaveBeenCalledWith({ reason: "other", waterbody_id: 9, detail: "Gate is locked" }),
    );
    expect(onSent).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("sends a missing lake at the middle of the map", async () => {
    render(
      <LakeReportDialog
        target={{ kind: "missing", point: { latitude: 30.27, longitude: -97.74 } }}
        open
        onClose={vi.fn()}
        onSent={vi.fn()}
      />,
    );
    expect(session.getLakeReportOptions).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Lake name"), { target: { value: "Mystery Pond" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() =>
      expect(session.reportLake).toHaveBeenCalledWith({ reason: "missing", name: "Mystery Pond", latitude: 30.27, longitude: -97.74 }),
    );
  });

  it("keeps the form and says why when sending fails", async () => {
    const { ApiError } = await import("@/lib/api/client");
    vi.mocked(session.reportLake).mockRejectedValue(new ApiError("You've sent a lot of reports. Try again later.", 429));
    render(<LakeReportDialog target={{ kind: "problem", lakeId: 9, lakeName: "Lake Fork" }} open onClose={vi.fn()} onSent={vi.fn()} />);
    fireEvent.click(await screen.findByRole("radio", { name: "It isn't open to the public" }));
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("a lot of reports");
  });
});
