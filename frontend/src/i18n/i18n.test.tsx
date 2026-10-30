import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

import { LanguageMenu, LanguageSuggestion } from "@/components/LanguageMenu";
import { WaterLine } from "@/components/community/PinForm";
import { lakeRange } from "@/components/waterbody/WeatherRecommendations";
import { I18nProvider } from "./client";
import { preferredLocale } from "./config";
import { MESSAGES } from "./messages";
import { FISH_NAMES, GROUP_NAMES, HANDBOOK_TITLES, STATE_NAMES, localGroup, localSpecies, withoutArticle } from "./names";
import { localWindSpeed } from "./weather";

/** Every leaf of a dictionary, as "path: value", functions called with
 * sample arguments so a template can't come out empty either. */
function leaves(node: unknown, path = ""): [string, string][] {
  if (typeof node === "string") return [[path, node]];
  if (typeof node === "function") return [[path, String((node as (...a: unknown[]) => unknown)("1", "1", "1"))]];
  if (Array.isArray(node)) return node.flatMap((v, i) => leaves(v, `${path}[${i}]`));
  return Object.entries(node as Record<string, unknown>).flatMap(([k, v]) => leaves(v, path ? `${path}.${k}` : k));
}

afterEach(() => {
  document.cookie = "fisheye.lang=; max-age=0; path=/";
  refresh.mockReset();
  vi.restoreAllMocks();
});

const OTHERS = ["zh", "es", "ko", "ja"] as const;

describe("the dictionaries", () => {
  it.each(OTHERS)("%s says everything English says, in its own words", (lang) => {
    const en = new Map(leaves(MESSAGES.en));
    const other = leaves(MESSAGES[lang]);
    expect(other.map(([p]) => p).sort()).toEqual([...en.keys()].sort());
    // English's empty string means "nothing to say" (legal.englishOnly).
    const empty = other.filter(([p, v]) => !v.trim() && en.get(p)?.trim());
    expect(empty).toEqual([]);
  });

  it("names every fish, handbook topic, look-alike group and state in every language", () => {
    for (const table of [FISH_NAMES, HANDBOOK_TITLES, GROUP_NAMES]) {
      const keys = Object.keys(table.zh).sort();
      for (const lang of OTHERS) expect(Object.keys(table[lang]).sort()).toEqual(keys);
    }
    for (const lang of OTHERS) expect(Object.keys(STATE_NAMES[lang])).toHaveLength(51);
    expect(localSpecies("bluegill", "Bluegill", "es")).toBe("Mojarra de agallas azules");
    expect(localSpecies(null, "Channel Catfish", "zh")).toBe("斑点叉尾鮰");
    expect(localSpecies(null, "Rainbow Trout", "ja")).toBe("ニジマス");
    expect(localSpecies(null, "Gar", "ko")).toBe("Gar");
  });

  it("joins a sentence split around a link in each language's own order", () => {
    const legal = (l: (typeof OTHERS)[number] | "en") => {
      const a = MESSAGES[l].auth;
      return a.legal1(13) + a.terms + a.and + a.privacy + a.legalEnd;
    };
    expect(legal("en")).toBe("By continuing you confirm you're 13 or older and agree to FishEye's terms and privacy policy.");
    expect(legal("zh")).toBe("继续即表示你确认已年满 13 岁，并同意 FishEye 的使用条款和隐私政策。");
    expect(legal("ko")).toBe("계속하면 만 13세 이상임을 확인하고 FishEye의 이용약관 및 개인정보 처리방침에 동의하게 돼요.");
    expect(legal("ja")).toBe("続行すると、13歳以上であることを確認し、FishEyeの利用規約とプライバシーポリシーに同意したものとみなされます。");
    const knot = (l: (typeof OTHERS)[number]) => MESSAGES[l].start.tieWith + MESSAGES[l].start.knot + MESSAGES[l].start.tieEnd;
    expect(knot("zh")).toBe("用改良克林奇结把钩绑在线上。");
    expect(knot("ko")).toBe("바늘은 개량 클린치 노트로 묶어요.");
    expect(knot("ja")).toBe("針はインプルーブドクリンチノットで結びます。");
  });

  it.each(OTHERS)("%s has none of the marks of a filled-in template", (lang) => {
    const found = leaves(MESSAGES[lang]).filter(
      ([, v]) =>
        /\((a|o|as|os)\)/.test(v) || // "un(a)": a gender left for the reader to pick
        / {2}/.test(v.trim()) ||
        ((lang === "zh" || lang === "ja") && /[぀-ヿ一-鿿]\.$/.test(v)), // an English full stop
    );
    expect(found).toEqual([]);
  });

  it("puts the photo check's look-alike group in the reader's words", () => {
    expect(localGroup("a black bass", "en")).toBe("a black bass");
    expect(localGroup("a black bass", "ko")).toBe("배스류");
    expect(localGroup("a catfish", "es")).toBe("un bagre");
    expect(withoutArticle(localGroup("a catfish", "es"))).toBe("bagre");
    expect(localGroup("a gar", "ja")).toBe("a gar");
  });

  it("writes wind speeds and times the way each language does", () => {
    expect(localWindSpeed("5 to 10 mph", "ja")).toBe("時速5〜10マイル");
    expect(localWindSpeed("10 mph", "ko")).toBe("시속 10마일");
    expect(localWindSpeed("5 to 10 mph", "zh")).toBe("5–10 英里/小时");
    expect(localWindSpeed("5 to 10 mph", "en")).toBe("5 to 10 mph");
    expect(localWindSpeed("Calm", "ja")).toBe("Calm");
    expect(lakeRange("2026-10-30T05:00:00-05:00", "2026-10-30T08:00:00-05:00", "ja")).toBe("5:00〜8:00");
    expect(lakeRange("2026-10-30T17:00:00-05:00", "2026-10-30T19:30:00-05:00", "ko")).toBe("17:00~19:30");
    expect(lakeRange("2026-10-30T05:00:00-05:00", "2026-10-30T08:00:00-05:00", "en")).toBe("5–8 AM");
  });
});

describe("choosing a language", () => {
  it("suggests a language only to a browser that prefers one of ours over English", () => {
    expect(preferredLocale(["zh-CN", "en-US"])).toBe("zh");
    expect(preferredLocale(["es-MX"])).toBe("es");
    expect(preferredLocale(["ko-KR", "ko", "en-US"])).toBe("ko");
    expect(preferredLocale(["ja"])).toBe("ja");
    expect(preferredLocale(["en-US", "zh-CN"])).toBeNull();
    expect(preferredLocale(["fr-FR"])).toBeNull();
  });

  it("switches from the header menu, keeping the choice in a cookie", () => {
    render(<LanguageMenu />);
    fireEvent.click(screen.getByRole("button", { name: "Language: English" }));
    fireEvent.click(screen.getByRole("menuitemradio", { name: "Español" }));
    expect(document.cookie).toContain("fisheye.lang=es");
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("offers Chinese, in Chinese, to a Chinese browser that hasn't chosen", () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["zh-CN", "en"]);
    render(<LanguageSuggestion />);
    fireEvent.click(screen.getByRole("button", { name: "使用中文" }));
    expect(document.cookie).toContain("fisheye.lang=zh");
    expect(refresh).toHaveBeenCalled();
  });

  it("says nothing once a language is chosen", () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["es-MX"]);
    document.cookie = "fisheye.lang=en; path=/";
    const { container } = render(<LanguageSuggestion />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("where the catch being placed is (backend ADR 0040)", () => {
  it("names the water, or says to move onto it, in the chosen language", () => {
    const { rerender } = render(
      <I18nProvider locale="es">
        <WaterLine water={{ state: "on", name: "Lake Lanier", kind: "lake" }} />
      </I18nProvider>,
    );
    expect(screen.getByText("En Lake Lanier")).toBeInTheDocument();
    const missing = vi.fn();
    rerender(
      <I18nProvider locale="zh">
        <WaterLine water={{ state: "off", required: true }} onMissingWater={missing} />
      </I18nProvider>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("把标记拖到水上");
    fireEvent.click(screen.getByRole("button", { name: "地图上没有这片水？告诉我们" }));
    expect(missing).toHaveBeenCalled();
  });
});
