/** @vitest-environment node */
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { LOCALE_PATHS } from "@/i18n/config";
import { config, proxy } from "./proxy";

describe("the proxy (docs/adr/0068)", () => {
  it("shows a language's address as the plain page in that language", () => {
    const res = proxy(new NextRequest("https://fisheyefishing.com/zh/rules/texas?ref=xhs"));
    expect(res.headers.get("x-middleware-rewrite")).toBe("https://fisheyefishing.com/rules/texas?ref=xhs");
    expect(res.headers.get("x-middleware-request-x-fisheye-locale")).toBe("zh");
    expect(res.cookies.get("fisheye.lang")?.value).toBe("zh");
  });

  it("shows the home page at a bare language address", () => {
    const res = proxy(new NextRequest("https://fisheyefishing.com/zh-tw"));
    expect(res.headers.get("x-middleware-rewrite")).toBe("https://fisheyefishing.com/");
    expect(res.headers.get("x-middleware-request-x-fisheye-locale")).toBe("zht");
  });

  it("leaves the cookie alone when it already says that language", () => {
    const req = new NextRequest("https://fisheyefishing.com/ja/fish", { headers: { cookie: "fisheye.lang=ja" } });
    expect(proxy(req).cookies.get("fisheye.lang")).toBeUndefined();
  });

  it("passes a plain address on untouched", () => {
    const res = proxy(new NextRequest("https://fisheyefishing.com/rules/texas"));
    expect(res.headers.get("x-middleware-rewrite")).toBeNull();
    expect(res.headers.get("x-middleware-next")).toBe("1");
  });

  it("runs on every language's address, and only on those", () => {
    const segments = Object.values(LOCALE_PATHS).filter(Boolean).join("|");
    expect(config.matcher).toEqual([`/(${segments})`, `/(${segments})/:path*`]);
  });
});
