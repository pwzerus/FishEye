"use client";

import { useLocale } from "@/i18n/client";
import { localFishName } from "@/i18n/names";

/** A fish's name in the chosen language, then its English name smaller:
 * the English one is what regulations, tackle shops and lake signs use.
 * Just the English name in English, or for a fish without a translation. */
export function FishName({ slug, english }: { slug: string; english: string }) {
  const locale = useLocale();
  return <FishNameParts local={localFishName(slug, locale)} english={english} />;
}

/** The same, for server components, which pass the name themselves. */
export function FishNameParts({ local, english }: { local: string | null; english: string }) {
  if (!local) return <>{english}</>;
  return (
    <>
      {local}
      <span className="name-en" lang="en">
        {english}
      </span>
    </>
  );
}
