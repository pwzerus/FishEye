"use client";

import { useT } from "@/i18n/client";
import type { PinSummary } from "@/lib/api/types";

export function Heart({ filled = false }: { filled?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 20.5s-7.5-4.6-9-10a4.8 4.8 0 0 1 9-3 4.8 4.8 0 0 1 9 3c-1.5 5.4-9 10-9 10z" />
    </svg>
  );
}

function Bubble() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 5h16v11H9l-5 4z" />
    </svg>
  );
}

/** Under a card in a list: how many, not a button (the whole card is a link). */
export function SocialCounts({ pin }: { pin: PinSummary }) {
  const t = useT().social;
  const likes = pin.like_count ?? 0;
  const comments = pin.comment_count ?? 0;
  if (likes === 0 && comments === 0) return null;
  return (
    <span className="pin-card-social">
      {likes > 0 && (
        <span aria-label={t.likes(likes)}>
          <Heart filled /> {likes}
        </span>
      )}
      {comments > 0 && (
        <span aria-label={t.commentCount(comments)}>
          <Bubble /> {comments}
        </span>
      )}
    </span>
  );
}
