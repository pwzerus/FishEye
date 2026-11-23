import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// The request headers and cookie the server helpers read (next/headers).
const request = vi.hoisted(() => ({ header: null as string | null, cookie: undefined as string | undefined }));
vi.mock("next/headers", () => ({
  headers: async () => new Headers(request.header ? { "x-fisheye-locale": request.header } : {}),
  cookies: async () => ({ get: () => (request.cookie ? { value: request.cookie } : undefined) }),
}));

import Link from "@/components/LocaleLink";
import { I18nProvider } from "./client";
import { LOCALES, localePath, splitLocalePath, type Locale } from "./config";
import { getLocale, pageAlternates } from "./server";

describe("language addresses (docs/adr/0068)", () => {
  it.each([
    ["/zh/rules/texas", "zh", "/rules/texas"],
    ["/zh", "zh", "/"],
    ["/zh/", "zh", "/"],
    ["/zh-tw/fish", "zht", "/fish"],
    ["/es", "es", "/"],
    ["/ko/map", "ko", "/map"],
    ["/rules", null, "/rules"],
    ["/", null, "/"],
    ["/zhx/rules", null, "/zhx/rules"],
    ["/ZH/rules", null, "/ZH/rules"],
    ["/en/rules", null, "/en/rules"],
  ])("%s names %s and shows %s", (address, locale, path) => {
    expect(splitLocalePath(address)).toEqual({ locale, path });
  });

  it.each([
    ["zh", "/rules", "/zh/rules"],
    ["zh", "/", "/zh"],
    ["zh", "/?ref=xhs", "/zh?ref=xhs"],
    ["zh", "/#top", "/zh#top"],
    ["zht", "/map?lake=5", "/zh-tw/map?lake=5"],
    ["ja", "/login?next=%2Fja%2Fask", "/ja/login?next=%2Fja%2Fask"],
    ["en", "/rules", "/rules"],
    ["es", "/zh/rules", "/zh/rules"],
    ["ko", "/api/ask", "/api/ask"],
    ["ko", "/_next/static/x.js", "/_next/static/x.js"],
    ["ko", "/brand/fisheye-mark.svg", "/brand/fisheye-mark.svg"],
    ["es", "https://tpwd.texas.gov/x", "https://tpwd.texas.gov/x"],
    ["es", "//evil.example/x", "//evil.example/x"],
    ["es", "#section", "#section"],
  ])("%s: %s is at %s", (locale, path, address) => {
    expect(localePath(locale as Locale, path)).toBe(address);
  });

  it("finds every language's page again", () => {
    for (const l of LOCALES) {
      expect(splitLocalePath(localePath(l, "/fish/largemouth-bass"))).toEqual({
        locale: l === "en" ? null : l,
        path: "/fish/largemouth-bass",
      });
    }
  });
});

describe("links keep the page's language", () => {
  it("points a Chinese page's links at Chinese addresses", () => {
    render(
      <I18nProvider locale="zh">
        <Link href="/rules/texas">规定</Link>
        <Link href={{ pathname: "/fish", query: { state: "TX" } }}>鱼</Link>
        <Link href="https://tpwd.texas.gov/">TPWD</Link>
      </I18nProvider>,
    );
    expect(screen.getByRole("link", { name: "规定" })).toHaveAttribute("href", "/zh/rules/texas");
    expect(screen.getByRole("link", { name: "鱼" })).toHaveAttribute("href", "/zh/fish?state=TX");
    expect(screen.getByRole("link", { name: "TPWD" })).toHaveAttribute("href", "https://tpwd.texas.gov/");
  });

  it("leaves English links as written", () => {
    render(<Link href="/rules/texas">Rules</Link>);
    expect(screen.getByRole("link", { name: "Rules" })).toHaveAttribute("href", "/rules/texas");
  });
});

describe("the page's language and addresses for search engines", () => {
  it("renders in the address's language over the visitor's choice", async () => {
    request.header = "ja";
    request.cookie = "es";
    expect(await getLocale()).toBe("ja");
    request.header = null;
    expect(await getLocale()).toBe("es");
    request.cookie = undefined;
    expect(await getLocale()).toBe("en");
  });

  it("names the address being read as canonical, and every language's", async () => {
    request.header = "zh";
    const zh = await pageAlternates("/rules/texas");
    expect(zh.canonical).toBe("/zh/rules/texas");
    expect(zh.languages).toEqual({
      en: "/rules/texas",
      "zh-Hans": "/zh/rules/texas",
      "zh-Hant": "/zh-tw/rules/texas",
      es: "/es/rules/texas",
      ko: "/ko/rules/texas",
      ja: "/ja/rules/texas",
      "x-default": "/rules/texas",
    });
    request.header = null;
    request.cookie = "zh";
    // A plain address is the English page to a search engine, whatever
    // this visitor chose.
    expect((await pageAlternates("/")).canonical).toBe("/");
  });
});
