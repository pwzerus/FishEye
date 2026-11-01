import { useEffect } from "react";

/** A link to something inside a closed <details> would land on nothing: open
 * the ones around the target, then go to it. */
export function useRevealHash() {
  useEffect(() => {
    const reveal = () => {
      let id: string;
      try { id = decodeURIComponent(window.location.hash.slice(1)); } catch { return; }
      if (!id) return;
      const target = document.getElementById(id);
      if (!target) return;
      let opened = false;
      for (let d = target.closest("details"); d; d = d.parentElement?.closest("details") ?? null) {
        if (!d.open) opened = true;
        d.open = true;
      }
      if (opened) target.scrollIntoView({ block: "start", behavior: "instant" });
    };
    reveal();
    window.addEventListener("hashchange", reveal);
    return () => window.removeEventListener("hashchange", reveal);
  }, []);
}
