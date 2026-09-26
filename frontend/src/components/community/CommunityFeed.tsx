"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { getPinOptions, listPins } from "@/lib/api/session";
import type { PinOptions, PinSummary } from "@/lib/api/types";
import { PinCard } from "./PinCard";

export function CommunityFeed() {
  const { user, loading: authLoading } = useAuth();
  const [pins, setPins] = useState<PinSummary[] | null>(null);
  const [options, setOptions] = useState<PinOptions | null>(null);
  const [species, setSpecies] = useState("");
  const [mine, setMine] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPinOptions().then(setOptions).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (authLoading) return;
    let cancelled = false;
    listPins({ species: species || undefined, mine: mine && !!user, limit: 120 })
      .then((p) => {
        if (!cancelled) {
          setPins(p);
          setError(null);
        }
      })
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [species, mine, user, authLoading]);

  const addHref = user ? "/map?addPin=1" : `/login?next=${encodeURIComponent("/map?addPin=1")}`;

  return (
    <>
      <section className="page-intro community-intro">
        <div>
          <p className="eyebrow reveal" style={{ "--i": 0 } as React.CSSProperties}>
            Community
          </p>
          <h1 className="reveal" style={{ "--i": 1 } as React.CSSProperties}>
            Where people are catching fish
          </h1>
          <p className="lede reveal" style={{ "--i": 2 } as React.CSSProperties}>
            Spots other anglers pinned, with their photos and notes. These are their reports, not
            verified survey data, and they never change what FishMate says a lake holds.
          </p>
        </div>
        <Link href={addHref} className="btn btn-primary reveal" style={{ "--i": 3 } as React.CSSProperties}>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
            <path d="M12 5v14M5 12h14" strokeLinecap="round" />
          </svg>
          Pin a catch
        </Link>
      </section>

      <div className="fish-toolbar reveal" style={{ "--i": 4 } as React.CSSProperties}>
        <div className="segmented" role="tablist" aria-label="Whose pins">
          <button type="button" role="tab" aria-selected={!mine} className={!mine ? "segment active" : "segment"} onClick={() => setMine(false)}>
            Everyone
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mine}
            disabled={!user}
            title={user ? undefined : "Sign in to see your own pins"}
            className={mine ? "segment active" : "segment"}
            onClick={() => setMine(true)}
          >
            My pins
          </button>
        </div>
        <label className="select-field">
          <span className="sr-only">Fish</span>
          <select value={species} onChange={(e) => setSpecies(e.target.value)}>
            <option value="">All fish</option>
            {options?.species.map((s) => (
              <option key={s.slug} value={s.slug}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? (
        <div className="backend-error">{error}</div>
      ) : pins === null ? (
        <ul className="pin-grid" aria-busy="true">
          {Array.from({ length: 6 }, (_, i) => (
            <li key={i} className="pin-card sk-card">
              <div className="sk" style={{ aspectRatio: "4 / 3", borderRadius: 0 }} />
              <div className="pin-card-body">
                <div className="sk sk-line" />
                <div className="sk sk-line short" />
              </div>
            </li>
          ))}
        </ul>
      ) : pins.length === 0 ? (
        <div className="empty-state reveal">
          <h2>{mine ? "You haven't pinned anything yet" : "No pins here yet"}</h2>
          <p className="muted">Be the first: open the map, tap where you fished, and add a photo.</p>
          <Link href={addHref} className="btn btn-primary btn-sm">
            Pin a catch
          </Link>
        </div>
      ) : (
        <ul className="pin-grid" key={`${species}-${mine}`}>
          {pins.map((p, i) => (
            <li key={p.id}>
              <PinCard pin={p} index={i} />
            </li>
          ))}
        </ul>
      )}

      <section className="rules-card community-rules">
        <h2>Community rules</h2>
        <ul>
          <li>Pin places you actually fished, where the public can legally fish.</li>
          <li>Only post photos you took. No faces of other people without their OK.</li>
          <li>Keep a spot to yourself by making the pin &quot;Only me&quot;. Location data inside photos is always removed.</li>
          <li>Anyone signed in can report a pin. Pins reported by several people are hidden until a moderator reviews them.</li>
        </ul>
      </section>
    </>
  );
}
