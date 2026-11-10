"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

import { API_BASE_URL } from "@/lib/api/session";

/**
 * Adds one to this page's count for the day (backend services/visits.py).
 *
 * Sends the page's path, the site the link came from (only its host is
 * kept) and a ?ref= tag if the link had one. No cookie goes with it
 * (credentials: "omit"), nothing is stored in the browser, and nothing
 * identifies the visitor; the privacy page says so. A browser driven by a
 * script (navigator.webdriver) isn't counted.
 */
export function VisitCounter() {
  const pathname = usePathname();
  const last = useRef<string | null>(null);
  // Only the first page of a visit came from somewhere else.
  const first = useRef(true);

  useEffect(() => {
    if (!pathname || pathname === last.current) return;
    last.current = pathname;
    if (typeof navigator !== "undefined" && navigator.webdriver) return;
    const ref = first.current ? new URLSearchParams(window.location.search).get("ref") : null;
    const referrer = first.current ? document.referrer || null : null;
    first.current = false;
    void fetch(`${API_BASE_URL}/api/visits`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: pathname, referrer, ref }),
      credentials: "omit",
      keepalive: true,
    }).catch(() => {
      // A count missed is nothing the visitor needs to hear about.
    });
  }, [pathname]);

  return null;
}
