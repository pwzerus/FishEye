type Point = { latitude: number; longitude: number };

/** Kilometres between two points, flat-earth: close enough to rank places
 * within a drive of each other. */
export function kmApart(a: Point, b: Point): number {
  const k = Math.PI / 180;
  const x = (b.longitude - a.longitude) * k * Math.cos(((a.latitude + b.latitude) / 2) * k);
  const y = (b.latitude - a.latitude) * k;
  return Math.hypot(x, y) * 6371;
}
