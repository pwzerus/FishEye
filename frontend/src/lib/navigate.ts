/** A full page load at `url`. The language menu uses it when the address
 * changes with the language ("/rules" to "/zh/rules"), so the header and
 * the page change together. A module of its own so tests can stand in for
 * it: jsdom can't navigate. */
export function loadPage(url: string): void {
  window.location.assign(url);
}
