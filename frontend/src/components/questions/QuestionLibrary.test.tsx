import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { LibraryQuestion } from "@/lib/api/types";
import { QuestionLibrary } from "./QuestionLibrary";

function question(id: string, category: string, text: string): LibraryQuestion {
  return { id, category, category_label: `${category} label`, question: text, short: "Short.", body: "Body.", basis: "guide", sources: [] } as unknown as LibraryQuestion;
}

const questions = [question("a", "reels", "How do I oil a reel?"), question("b", "reels", "Which reel first?"), question("c", "line", "When do I change line?")];

describe("QuestionLibrary", () => {
  it("shows every category until something is typed", () => {
    render(<QuestionLibrary questions={questions} lang="en" />);
    expect(screen.getByRole("link", { name: "reels label" })).toHaveAttribute("href", "#reels");
    expect(screen.getByText("When do I change line?")).toBeInTheDocument();
  });

  it("keeps only the matches and opens their categories", () => {
    const { container } = render(<QuestionLibrary questions={questions} lang="en" />);
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "OIL" } });
    expect(screen.getByText("How do I oil a reel?")).toBeInTheDocument();
    expect(screen.queryByText("Which reel first?")).toBeNull();
    expect(screen.queryByText("When do I change line?")).toBeNull();
    expect(container.querySelector("#reels")).toHaveAttribute("open");
  });

  it("says so when nothing matches", () => {
    render(<QuestionLibrary questions={questions} lang="en" />);
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "zzz" } });
    expect(screen.getByText(/No question matches/)).toBeInTheDocument();
  });
});
