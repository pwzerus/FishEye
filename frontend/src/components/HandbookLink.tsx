"use client";

import type { ReactNode } from "react";

import Link from "@/components/LocaleLink";
import { usePagePath } from "@/i18n/pagePath";

/**
 * A link to one handbook topic. Elsewhere it opens /handbook#<topic>; on the
 * handbook itself it is a plain #<topic> link, like the page's own chapter
 * links. Next.js moves to another hash of the page you're on with
 * pushState, which fires no hashchange, so the handbook kept the topic's
 * chapter hidden and a tap on a term card's "see the drawing" did nothing
 * (2026-11-25).
 */
export function HandbookLink({
  topic,
  className,
  onClick,
  children,
}: {
  topic: string;
  className?: string;
  onClick?: () => void;
  children: ReactNode;
}) {
  const path = usePagePath();
  if (path === "/handbook") {
    return (
      <a className={className} href={`#${topic}`} onClick={onClick}>
        {children}
      </a>
    );
  }
  return (
    <Link className={className} href={`/handbook#${topic}`} onClick={onClick}>
      {children}
    </Link>
  );
}
