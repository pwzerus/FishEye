/** How many pixels at the bottom of the map `cover` hides: a phone's sheet
 * lies over the map; beside it (desktop) or below it, it hides nothing. */
export function coveredBottom(map: DOMRect, cover: DOMRect | null): number {
  if (!cover || cover.left >= map.right || cover.right <= map.left) return 0;
  return Math.max(0, Math.min(map.bottom, cover.bottom) - Math.max(map.top, cover.top));
}
