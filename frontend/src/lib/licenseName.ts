/** A photo licence's name for display: "Public domain" in the reader's
 * language; the Creative Commons names (CC0, CC BY 4.0) are the same in all. */
export function licenseName(license: string, publicDomain: string): string {
  return license.toLowerCase() === "public domain" ? publicDomain : license;
}
