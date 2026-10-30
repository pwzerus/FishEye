/**
 * Keeps the site up while the browser translates it.
 *
 * Chrome's and Edge's "Translate this page" swap each text node for a <font>
 * holding the translation. React still holds the old text node, and its next
 * update removes it from (or inserts before it in) a parent it has left: a
 * DOMException that blanks the whole page (facebook/react#11538). The
 * visiting angler in the 2026-10-29 persona doc, who reads English slowly,
 * is exactly who translates the page. With these guards the update that
 * would have crashed does nothing instead: a translated line may go stale
 * until the page reloads, but the page stays up. Nothing changes for a page
 * no one translated, where the parents always match.
 */
export function guardAgainstPageTranslation(): void {
  if (typeof Node !== "function") return;
  const proto = Node.prototype as Node & { fisheyeTranslateGuard?: true };
  if (proto.fisheyeTranslateGuard) return;
  proto.fisheyeTranslateGuard = true;

  const removeChild = proto.removeChild;
  proto.removeChild = function (this: Node, child: Node) {
    if (child.parentNode !== this) return child;
    return removeChild.call(this, child);
  } as typeof proto.removeChild;

  const insertBefore = proto.insertBefore;
  proto.insertBefore = function (this: Node, node: Node, ref: Node | null) {
    if (ref && ref.parentNode !== this) return node;
    return insertBefore.call(this, node, ref);
  } as typeof proto.insertBefore;
}
