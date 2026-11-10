"use client";

import { useEffect } from "react";

/** The handbook used to be part of /fish. A link saved then ("/fish#care")
 * names something that isn't on this page any more: send it on. */
export function HandbookRedirect() {
  useEffect(() => {
    let id = "";
    try {
      id = decodeURIComponent(window.location.hash.slice(1));
    } catch {
      return;
    }
    if (id && !document.getElementById(id)) window.location.replace(`/handbook#${encodeURIComponent(id)}`);
  }, []);
  return null;
}
