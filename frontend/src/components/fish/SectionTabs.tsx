"use client";

import { useEffect, useRef, useState } from "react";

export interface SectionLink {
  id: string;
  label: string;
}

/**
 * Sticky in-page tabs. The active tab follows the scroll position, and the
 * pill slides between tabs instead of jumping (the indicator is one element
 * positioned under whichever tab is active).
 */
export function SectionTabs({ links }: { links: SectionLink[] }) {
  const [active, setActive] = useState(links[0]?.id);
  const navRef = useRef<HTMLElement>(null);
  const [pill, setPill] = useState<{ left: number; width: number } | null>(null);

  useEffect(() => {
    const els = links.map((l) => document.getElementById(l.id)).filter((e): e is HTMLElement => !!e);
    if (els.length === 0 || typeof IntersectionObserver === "undefined") return;
    const visible = new Map<string, number>();
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) visible.set(e.target.id, e.isIntersecting ? e.boundingClientRect.top : Infinity);
        const best = [...visible.entries()].filter(([, top]) => top !== Infinity).sort((a, b) => a[1] - b[1])[0];
        if (best) setActive(best[0]);
      },
      { rootMargin: "-120px 0px -55% 0px" },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [links]);

  useEffect(() => {
    const nav = navRef.current;
    const el = nav?.querySelector<HTMLAnchorElement>(`a[data-id="${active}"]`);
    if (!nav || !el) return;
    setPill({ left: el.offsetLeft, width: el.offsetWidth });
    // Keep the active tab visible when the bar scrolls sideways on phones.
    const target = el.offsetLeft - nav.clientWidth / 2 + el.offsetWidth / 2;
    if (typeof nav.scrollTo === "function") nav.scrollTo({ left: target, behavior: "smooth" });
  }, [active]);

  return (
    <nav ref={navRef} className="section-tabs" aria-label="On this page">
      {pill && <span className="section-pill" style={{ left: pill.left, width: pill.width }} aria-hidden="true" />}
      {links.map((l) => (
        <a
          key={l.id}
          href={`#${l.id}`}
          data-id={l.id}
          className={active === l.id ? "section-tab active" : "section-tab"}
          aria-current={active === l.id ? "true" : undefined}
          onClick={() => setActive(l.id)}
        >
          {l.label}
        </a>
      ))}
    </nav>
  );
}
