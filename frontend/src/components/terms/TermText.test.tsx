import { fireEvent, render, screen } from "@testing-library/react";
import { StrictMode } from "react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/baits", () => ({ useBaitCards: () => null, findBaits: () => [] }));

import { I18nProvider } from "@/i18n/client";
import { LOCALES } from "@/i18n/config";
import { MESSAGES } from "@/i18n/messages";
import { HANDBOOK_TITLES } from "@/i18n/names";
import { findTerms, TERM_TOPIC, type TermId } from "@/lib/terms";
import { LinkedItems, LinkedText } from "./TermText";

const en = MESSAGES.en.terms.items;
const ids = (text: string, locale: (typeof LOCALES)[number] = "en", skipTopic: string | null = null) =>
  findTerms(text, locale, MESSAGES[locale].terms.items, en, { skipTopic, max: 10 }).map((m) => m.id);

describe("fishing terms", () => {
  it("explains every term in a handbook topic that exists, in every language", () => {
    for (const topic of Object.values(TERM_TOPIC)) expect(HANDBOOK_TITLES.zh[topic], topic).toBeTruthy();
    for (const locale of LOCALES) {
      for (const id of Object.keys(TERM_TOPIC) as TermId[]) {
        const t = MESSAGES[locale].terms.items[id];
        expect(t.name.trim(), `${locale} ${id}`).not.toBe("");
        expect(t.def.trim(), `${locale} ${id}`).not.toBe("");
      }
    }
  });

  it("finds the terms a sentence names, each once, longest first", () => {
    expect(ids("Tie the barrel swivel on with a Palomar knot, then set the drag.")).toEqual(["swivel", "palomar", "drag"]);
    expect(ids("A slip bobber slides down to the bobber stop; the bobber shows the bite.")).toEqual(["slipBobber", "bobberStop", "bobber"]);
    expect(ids("穿心铅在桶形转环上方滑动，前导线接在转环下方。", "zh")).toEqual(["eggSinker", "swivel", "leader"]);
    expect(ids("구멍봉돌 아래에 도래를 달고, 목줄을 묶어요.", "ko")).toEqual(["eggSinker", "swivel", "leader"]);
    // Traditional Chinese is generated from the Simplified, its terms too.
    expect(ids("穿心鉛在桶形轉環上方滑動，前導線接在轉環下方。", "zht")).toEqual(["eggSinker", "swivel", "leader"]);
  });

  it("leaves the everyday meanings alone", () => {
    expect(ids("Drag it slowly along the bottom.")).toEqual([]);
    expect(ids("Spool up the line.")).toEqual([]);
    // 찌 (a bobber) is in 찌개 (a stew) and 찌르다 (to stab).
    expect(ids("김치찌개를 먹고 가시에 찌르지 않게 조심해요.", "ko")).toEqual([]);
    expect(ids("찌를 달아요.", "ko")).toEqual(["bobber"]);
    // Read off the handbook in every language (2026-11-16).
    expect(ids("小心胸鳍和背鳍上带倒刺的硬棘。", "zh")).toEqual([]);
    expect(ids("미늘 달린 가시를 조심하세요.", "ko")).toEqual([]);
    expect(ids("用钳子把倒刺压平。", "zh")).toEqual(["barb"]);
    expect(ids("How to fish: jig a small spoon up and down.")).toEqual([]);
    expect(ids("A spawn sac on a small hook.")).toEqual([]);
    expect(ids("魚の大きさに合わせてサイズを選びます。", "ja")).toEqual([]);
    expect(ids("リールのカバーを外します。", "ja")).toEqual([]);
    expect(ids("水草やカバーの中を引きます。", "ja")).toEqual(["cover"]);
    expect(ids("Detrás de una maraña de raíces.", "es")).toEqual([]);
    expect(ids("Streams fed by spawning runs give fast action.")).toEqual(["spawn"]);
  });

  it("doesn't link a topic's own card to itself", () => {
    expect(ids("The Palomar knot is easy.", "en", "knot-palomar")).toEqual([]);
  });

  it("opens a card that says what the term is, and links to its topic", () => {
    render(
      <I18nProvider locale="zh">
        <p>
          <LinkedText text="用帕洛马结绑钩。" />
        </p>
      </I18nProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "帕洛马结" }));
    const card = screen.getByRole("dialog", { name: "帕洛马结" });
    expect(card).toHaveTextContent(MESSAGES.zh.terms.items.palomar.def);
    // A Chinese page links to the Chinese address (docs/adr/0068).
    expect(card.querySelector("a")?.getAttribute("href")).toBe("/zh/handbook#knot-palomar");
    // The Palomar topic has a drawing, and the link says so.
    expect(card.querySelector("a")?.textContent).toBe(MESSAGES.zh.terms.moreDrawing(HANDBOOK_TITLES.zh["knot-palomar"]));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  // React renders twice in development: a set shared between renders had
  // been filled by the first and left the second linking nothing.
  it("links each term once in a list, rendered twice or not", () => {
    const { container } = render(
      <StrictMode>
        <I18nProvider locale="en">
          <ul>
            <LinkedItems items={["Use a leader and a swivel.", "A leader of fluorocarbon.", "Then a split shot."]} />
          </ul>
        </I18nProvider>
      </StrictMode>,
    );
    expect([...container.querySelectorAll("button.term")].map((b) => b.textContent)).toEqual(["leader", "swivel", "fluorocarbon", "split shot"]);
  });
});
