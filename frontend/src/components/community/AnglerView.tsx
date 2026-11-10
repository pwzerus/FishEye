"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useLocaleTag, useT } from "@/i18n/client";
import { getAngler, listPins } from "@/lib/api/session";
import type { Angler, PinSummary } from "@/lib/api/types";
import { formatDay, PinCard } from "./PinCard";

/** One angler's public catches. Only what they already show everyone. */
export function AnglerView({ id }: { id: number }) {
  const all = useT();
  const t = all.social;
  const tag = useLocaleTag();
  const { user, loading } = useAuth();
  const [angler, setAngler] = useState<Angler | null | undefined>(undefined);
  const [pins, setPins] = useState<PinSummary[] | null>(null);

  useEffect(() => {
    if (loading) return;
    getAngler(id).then(setAngler).catch(() => setAngler(null));
    listPins({ author: id, limit: 120 }).then(setPins).catch(() => setPins([]));
  }, [id, loading, user]);

  if (angler === undefined) {
    return (
      <div aria-busy="true">
        <div className="sk sk-title" />
        <div className="sk sk-line" />
      </div>
    );
  }
  if (angler === null) {
    return (
      <div className="empty-state">
        <h1>{t.anglerGone}</h1>
        <Link href="/community" className="btn btn-primary btn-sm">
          {all.catch.backToCatches}
        </Link>
      </div>
    );
  }
  return (
    <>
      <Link href="/community" className="back-link" transitionTypes={["nav-back"]}>
        <span aria-hidden="true">←</span> {all.nav.catches}
      </Link>
      <header className="angler-hero reveal">
        <span className="acct-avatar" aria-hidden="true">
          {angler.display_name.slice(0, 1).toUpperCase()}
        </span>
        <div>
          <h1>{angler.display_name}</h1>
          <p className="muted">{t.memberSince(formatDay(angler.joined_at, tag) ?? "")}</p>
        </div>
        <div className="acct-stats">
          <div>
            <strong>{angler.catches}</strong>
            <span>{t.statShared}</span>
          </div>
          <div>
            <strong>{angler.confirmed}</strong>
            <span>{t.statConfirmed}</span>
          </div>
          <div>
            <strong>{angler.likes}</strong>
            <span>{t.statLikes}</span>
          </div>
        </div>
      </header>
      {pins === null ? (
        <div className="sk" style={{ height: 240 }} />
      ) : (
        <ul className="pin-grid">
          {pins.map((p, i) => (
            <li key={p.id}>
              <PinCard pin={p} index={i} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
