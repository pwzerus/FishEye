"use client";

import Link from "next/link";
import { useState } from "react";

import { useLocale, useT } from "@/i18n/client";
import { localFishName } from "@/i18n/names";
import { ApiError, getSpeciesGuide, speciesSlug } from "@/lib/api/client";
import type { SpeciesGuide } from "@/lib/api/types";
import { SpeciesGuideBody } from "./SpeciesGuideBody";

/**
 * "How to catch it" under a species in a lake's panel. Closed by default and
 * fetched on first open: a lake can list half a dozen species, and most
 * people only want one of them.
 */
export function SpeciesHowTo({ commonName }: { commonName: string }) {
  const [open, setOpen] = useState(false);
  const [guide, setGuide] = useState<SpeciesGuide | null>(null);
  const [error, setError] = useState<string | null>(null);
  const slug = speciesSlug(commonName);
  const t = useT().lake;
  const locale = useLocale();

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next && guide === null) {
      setError(null);
      getSpeciesGuide(slug)
        .then(setGuide)
        .catch((e: unknown) => {
          setError(
            e instanceof ApiError && e.status === 404 ? t.noGuide : t.guideError,
          );
        });
    }
  }

  return (
    <div className="species-howto">
      <button type="button" className="species-howto-toggle" onClick={toggle} aria-expanded={open}>
        {open ? t.hideHowTo : t.howTo}
      </button>
      {open && (
        <div className="species-howto-content">
          {error && <p className="panel-error">{error}</p>}
          {!error && !guide && <p className="muted">{t.loadingGuide}</p>}
          {guide && (
            <>
              <SpeciesGuideBody guide={guide} compact />
              <Link href={`/fish/${slug}`} className="species-howto-full">
                {t.fullGuide(localFishName(guide.slug, locale) ?? guide.common_name)}
              </Link>
            </>
          )}
        </div>
      )}
    </div>
  );
}
