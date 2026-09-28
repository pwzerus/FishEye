"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AccountMenu } from "@/components/auth/AccountMenu";

/**
 * The one piece of chrome that never moves. It lives in the root layout and
 * carries its own view-transition name (globals.css pins it), so when page
 * content slides between routes the header stays put as the reference
 * point — the user sees the content move, not the whole app.
 *
 * Nav links carry a direction: moving right along the nav slides content
 * left ("forward"), moving left slides it right ("back"), the same way
 * swiping between tabs does.
 */

const NAV = [
  { href: "/", label: "Home", icon: "home" },
  { href: "/map", label: "Map", icon: "map" },
  { href: "/fish", label: "Fish guide", icon: "fish" },
  { href: "/community", label: "Community", icon: "community" },
  { href: "/ask", label: "Ask", icon: "ask" },
] as const;

function sectionIndex(pathname: string): number {
  const i = NAV.findIndex((n) => n.href !== "/" && pathname.startsWith(n.href));
  return i === -1 ? 0 : i;
}

function NavIcon({ name }: { name: (typeof NAV)[number]["icon"] }) {
  const common = {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  switch (name) {
    case "home":
      return (
        <svg {...common}>
          <path d="M3 11l9-7 9 7" />
          <path d="M5 10v10h14V10" />
        </svg>
      );
    case "map":
      return (
        <svg {...common}>
          <path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2z" />
          <path d="M9 4v14M15 6v14" />
        </svg>
      );
    case "fish":
      return (
        <svg {...common}>
          <path d="M3 12c3-5 9-6 13-3l5-3v12l-5-3c-4 3-10 2-13-3z" />
          <circle cx="8" cy="11" r="0.8" fill="currentColor" />
        </svg>
      );
    case "community":
      return (
        <svg {...common}>
          <path d="M12 21s-6-5.3-6-10a6 6 0 0 1 12 0c0 4.7-6 10-6 10z" />
          <circle cx="12" cy="11" r="2.2" />
        </svg>
      );
    case "ask":
      return (
        <svg {...common}>
          <path d="M4 5h16v11H9l-5 4V5z" />
          <path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.4" />
          <circle cx="12" cy="14.6" r="0.6" fill="currentColor" />
        </svg>
      );
  }
}

export function SiteHeader() {
  const pathname = usePathname() ?? "/";
  const current = sectionIndex(pathname);
  const onRoot = pathname === "/";

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <Link
          href="/"
          className="brand-link"
          aria-label="FishEye home"
          transitionTypes={onRoot ? undefined : ["nav-back"]}
        >
          <picture>
            <source srcSet="/brand/fisheye-lockup-dark.svg" media="(prefers-color-scheme: dark)" />
            {/* A static SVG logo: next/image would add nothing here. */}
            <img src="/brand/fisheye-lockup.svg" alt="FishEye" className="brand-lockup" />
          </picture>
          {/* On narrow screens the wordmark gives way to the mark alone. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/fisheye-mark.svg" alt="" className="brand-mark" aria-hidden="true" />
        </Link>
        <div className="site-header-right">
        <nav className="site-nav" aria-label="Main">
          {NAV.map((item, i) => {
            const active = i === current && (item.href !== "/" || onRoot);
            const direction = i > current ? "nav-forward" : "nav-back";
            return (
              <Link
                key={item.href}
                href={item.href}
                className={active ? "site-nav-link active" : "site-nav-link"}
                aria-current={active ? "page" : undefined}
                transitionTypes={active ? undefined : [direction]}
              >
                <NavIcon name={item.icon} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <AccountMenu />
        </div>
      </div>
    </header>
  );
}
