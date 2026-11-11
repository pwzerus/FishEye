"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Segmented } from "@/components/ui/Segmented";
import { useT } from "@/i18n/client";
import { getLeaderboard } from "@/lib/api/session";
import type { Leaderboard as Board, LeaderboardMetric, LeaderboardPeriod } from "@/lib/api/types";

const METRICS: LeaderboardMetric[] = ["catches", "shares", "active", "likes"];

/** A name's first letter (or character), for the round badge beside it. */
function initial(name: string): string {
  return (Array.from(name.trim())[0] ?? "?").toUpperCase();
}

/** Who has done the most in the place being browsed (backend services/social.py). */
export function Leaderboard({ state, county, where }: { state?: string; county?: string; where: string | null }) {
  const t = useT().social;
  const { user, loading } = useAuth();
  const [metric, setMetric] = useState<LeaderboardMetric>("catches");
  const [period, setPeriod] = useState<LeaderboardPeriod>("30d");
  const key = `${metric}:${period}:${state ?? ""}:${county ?? ""}:${user?.id ?? ""}`;
  const [result, setResult] = useState<{ key: string; board: Board | null } | null>(null);

  useEffect(() => {
    if (loading) return;
    let cancelled = false;
    getLeaderboard({ metric, period, state, county })
      .then((board) => !cancelled && setResult({ key, board }))
      .catch(() => !cancelled && setResult({ key, board: null }));
    return () => {
      cancelled = true;
    };
  }, [metric, period, state, county, loading, key]);

  const board = result?.key === key ? result.board : undefined;
  const label = { catches: t.metricCatches, shares: t.metricShares, active: t.metricActive, likes: t.metricLikes };
  const help = { catches: t.helpCatches, shares: t.helpShares, active: t.helpActive, likes: t.helpLikes };
  const unit = { catches: t.unitCatches, shares: t.unitShares, active: t.unitActive, likes: t.unitLikes };

  return (
    <section className="lb" aria-label={t.board}>
      <div className="lb-head">
        <span className="lb-trophy" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M8.5 20h7M10 17h4" />
          </svg>
        </span>
        <h2>{where ? t.boardIn(where) : t.boardAll}</h2>
      </div>
      <Segmented className="lb-tabs" label={t.board} value={metric} onChange={setMetric} options={METRICS.map((m) => ({ value: m, label: label[m] }))} />
      <div className="lb-sub">
        <p className="lb-help" key={metric}>
          {help[metric]}
        </p>
        <Segmented
          className="lb-period"
          label={t.period}
          value={period}
          onChange={setPeriod}
          options={[
            { value: "30d", label: t.month },
            { value: "all", label: t.allTime },
          ]}
        />
      </div>

      {board === undefined ? (
        <ol className="lb-list" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <li key={i} className="lb-sk">
              <span className="sk lb-sk-dot" />
              <span className="sk sk-line" />
            </li>
          ))}
        </ol>
      ) : board === null ? (
        <p className="lb-note">{t.failed}</p>
      ) : board.entries.length === 0 ? (
        <p className="lb-note lb-empty">{t.boardEmpty}</p>
      ) : (
        <ol className="lb-list" key={key}>
          {board.entries.map((e, i) => (
            <li key={e.user_id} className={e.is_me ? "is-me" : undefined} style={{ "--i": Math.min(i, 10) } as CSSProperties}>
              <span className={`lb-rank rank-${e.rank}`}>{e.rank}</span>
              <span className="lb-avatar" aria-hidden="true" style={{ "--h": (e.user_id * 47) % 360 } as CSSProperties}>
                {initial(e.display_name)}
              </span>
              <Link href={`/community/anglers/${e.user_id}`}>{e.is_me ? t.you(e.display_name) : e.display_name}</Link>
              <span className="lb-value">{unit[metric](e.value)}</span>
            </li>
          ))}
        </ol>
      )}
      {board?.me && !board.entries.some((e) => e.is_me) && (
        <p className="lb-me">
          {t.yourRank(board.me.rank)} · {unit[metric](board.me.value)}
        </p>
      )}
    </section>
  );
}
