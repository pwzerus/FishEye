/**
 * The fish and gear photos come up to 960px wide (backend
 * knowledge/gear_photos.py, services/species_photos.py), and most are drawn
 * far smaller: 56px on /start, 72px in the fish list, 96px on the handbook.
 * With smaller copies in a srcset, a phone loads the size it draws, not the
 * whole photo.
 *
 * Wikimedia makes its thumbnails on request at its standard widths (330, 500,
 * 960…), from a 960px thumbnail's URL or from an original file's. The gear
 * photos FishEye keeps itself (/gear-photos, from Flickr) have a 500px copy
 * in /gear-photos/500 (photoSizes.test.ts checks every one does).
 */
const COMMONS_960 = /\/960px-([^/]+)$/;
const COMMONS_ORIGINAL =
  /^(https:\/\/upload\.wikimedia\.org\/wikipedia\/commons)\/([0-9a-f]\/[0-9a-f]{2})\/([^/?]+\.(?:jpe?g|png|webp))(?:\?.*)?$/i;
const OWN = /^\/gear-photos\/([^/]+)$/;
const STEPS = [330, 500];

export function photoSrcSet(url: string, width?: number): string | undefined {
  if (COMMONS_960.test(url)) {
    return [...STEPS.map((w) => `${url.replace(COMMONS_960, `/${w}px-$1`)} ${w}w`), `${url} 960w`].join(", ");
  }
  const original = url.match(COMMONS_ORIGINAL);
  if (original && width) {
    const [, commons, dir, file] = original;
    const smaller = STEPS.filter((w) => w < width);
    if (smaller.length === 0) return undefined;
    return [...smaller.map((w) => `${commons}/thumb/${dir}/${file}/${w}px-${file} ${w}w`), `${url} ${width}w`].join(", ");
  }
  const own = url.match(OWN);
  if (own && width && width > 500) return `/gear-photos/500/${own[1]} 500w, ${url} ${width}w`;
  return undefined;
}

/** `src`, plus `srcSet` and `sizes` (how wide it is drawn) when there are
 * smaller copies to pick from. */
export function sized(url: string, width: number | undefined, sizes: string) {
  const srcSet = photoSrcSet(url, width);
  return srcSet ? { src: url, srcSet, sizes } : { src: url };
}
