/** "New York" → "new-york": the address of a state's rules page
 * (app/rules/[state]). A name, not the code, because it is what people
 * search for ("new york fishing license"). */
export function stateSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
