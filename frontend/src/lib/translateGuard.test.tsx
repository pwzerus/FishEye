import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { guardAgainstPageTranslation } from "./translateGuard";

/** What Chrome's translator does to a text node: puts a <font> holding the
 * translation in its place, leaving React's node detached. */
function translate(text: ChildNode) {
  const font = document.createElement("font");
  font.textContent = "蓝鳃太阳鱼";
  text.parentNode!.replaceChild(font, text);
}

// Two text nodes, so React removes the second one by itself (a lone text
// child is cleared through textContent, which never fails).
function Species() {
  const [shown, setShown] = useState(true);
  return (
    <div>
      <button type="button" onClick={() => setShown(false)}>
        Hide
      </button>
      <p data-testid="name">
        {"Fish: "}
        {shown ? "Bluegill" : null}
      </p>
    </div>
  );
}

/** The errors React reports while `act` runs (React 19 reports an uncaught
 * commit error to window rather than throwing it at the caller). */
function errorsDuring(act: () => void): unknown[] {
  const errors: unknown[] = [];
  const onError = (e: ErrorEvent) => {
    errors.push(e.error);
    e.preventDefault();
  };
  window.addEventListener("error", onError);
  try {
    act();
  } catch (e) {
    errors.push(e);
  } finally {
    window.removeEventListener("error", onError);
  }
  return errors;
}

describe("guardAgainstPageTranslation", () => {
  guardAgainstPageTranslation();

  it("lets React update a page the browser translated, instead of crashing", () => {
    render(<Species />);
    translate(screen.getByTestId("name").childNodes[1]);
    // React now removes the "Bluegill" text node from a <p> it has left.
    expect(errorsDuring(() => fireEvent.click(screen.getByRole("button", { name: "Hide" })))).toEqual([]);
    expect(screen.getByRole("button", { name: "Hide" })).toBeInTheDocument();
  });

  it("changes nothing for a page no one translated", () => {
    const p = document.createElement("p");
    const a = p.appendChild(document.createElement("span"));
    const b = document.createElement("span");
    p.insertBefore(b, a);
    expect([...p.childNodes]).toEqual([b, a]);
    p.removeChild(a);
    expect(a.parentNode).toBeNull();
    expect(() => p.removeChild(a)).not.toThrow(); // already gone: a no-op, as for a translated node
  });
});
