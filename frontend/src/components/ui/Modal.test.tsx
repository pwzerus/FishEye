import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { Modal } from "./Modal";

/** How most callers use it: the dialog is in the page only while open. */
function Harness() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Tell us
      </button>
      {open && (
        <Modal open title="A lake that's missing" onClose={() => setOpen(false)}>
          <p>Where is it?</p>
        </Modal>
      )}
    </>
  );
}

describe("Modal", () => {
  it("gives focus back to what opened it when it goes away", () => {
    render(<Harness />);
    const opener = screen.getByRole("button", { name: "Tell us" });
    opener.focus();
    fireEvent.click(opener);
    expect(screen.getByText("Where is it?")).toBeInTheDocument();
    // A browser's showModal moves focus into the dialog; jsdom doesn't.
    const close = screen.getByRole("button", { name: "Close" });
    close.focus();

    fireEvent.click(close);
    expect(screen.queryByText("Where is it?")).not.toBeInTheDocument();
    expect(document.activeElement).toBe(opener);
  });
});
