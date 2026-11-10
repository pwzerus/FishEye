"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useT } from "@/i18n/client";
import { getLeaderboard } from "@/lib/api/session";
import type { Leaderboard as Board, LeaderboardMetric, LeaderboardPeriod } from "@/lib/api/types";

const METRICS: LeaderboardMetric[] = ["catches", "shares", "active", "likes"];

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
    <section className="leaderboard" aria-label={t.board}>
      <h2>{where ? t.boardIn(where) : t.boardAll}</h2>
      <div className="lb-metrics" role="tablist" aria-label={t.board}>
        {METRICS.map((m) => (
          <button key={m} type="button" role="tab" aria-selected={m === metric} className={m === metric ? "lb-metric active" : "lb-metric"} onClick={() => setMetric(m)}>
            {label[m]}
          </button>
        ))}
      </div>
      <div className="lb-period">
        <p className="muted small">{help[metric]}</p>
        <label className="sr-only" htmlFor="lb-period">
          {t.period}
        </label>
        <select id="lb-period" value={period} onChange={(e) => setPeriod(e.target.value as LeaderboardPeriod)}>
          <option value="30d">{t.month}</option>
          <option value="all">{t.allTime}</option>
        </select>
      </div>

      {board === undefined ? (
        <div aria-busy="true">
          <div className="sk sk-line" />
          <div className="sk sk-line short" />
        </div>
      ) : board === null ? (
        <p className="muted small">{t.failed}</p>
      ) : board.entries.length === 0 ? (
        <p className="muted small lb-empty">{t.boardEmpty}</p>
      ) : (
        <ol className="lb-list">
          {board.entries.map((e) => (
            <li key={e.user_id} className={e.is_me ? "is-me" : undefined}>
              <span className={`lb-rank rank-${e.rank}`}>{e.rank}</span>
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
