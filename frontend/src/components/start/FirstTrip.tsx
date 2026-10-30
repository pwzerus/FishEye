"use client";

import Link from "next/link";
import { useState } from "react";

import { Modal } from "@/components/ui/Modal";
import { StatePicker } from "@/components/ui/StatePicker";
import { milesNumber } from "@/components/waterbody/NearbyShops";
import { listWaterbodies } from "@/lib/api/client";
import type { Jurisdiction, WaterbodyListItem } from "@/lib/api/types";
import { kmApart } from "@/lib/geo";
import { useLocale, useT } from "@/i18n/client";
import { localStateName } from "@/i18n/names";
import { useJurisdictions, useSelectedState } from "@/lib/jurisdiction";

/**
 * A first fishing trip in five steps, for someone who has never been: the
 * 14–18-year-old beginner the 2026-10-29 persona doc puts first. The handbook
 * already says all of it, in 80-odd cards; what a beginner lacks is the order
 * and the first thing to do (lapsed anglers name "where to fish" and "how to
 * get started" as what stopped them: ASA, Why Anglers Quit, 2025). Each step
 * is a line or two and one action, and links to the card that says more.
 */

/** TPWD's beginner's kit — "a rod and reel, a few hooks, split shot and
 * bobbers, and a tub of worms" (handbook start-first-trip) — plus pliers for
 * the hook (safe-handling). Hook size from the hooks card (bluegill No. 4–8). */
export const KIT = [
  // US hook sizes: a Korean 6호 or a Japanese 6号 is a different hook.
  { en: "Rod and reel combo (spincast or spinning)", zh: "竿轮套装（封闭轮或纺车轮）", es: "Combo de caña y carrete (spincast o spinning)", ko: "낚싯대와 릴 세트(스핀캐스트 또는 스피닝)", ja: "竿とリールのセット（スピンキャストかスピニング）", topic: "tackle-reels" },
  { en: "Small bobbers", zh: "小浮漂", es: "Boyas pequeñas", ko: "작은 찌", ja: "小さめのウキ", topic: "tackle-bobbers" },
  { en: "Hooks, size 6 or 8", zh: "鱼钩，美国号数 6 或 8", es: "Anzuelos, tamaño 6 u 8", ko: "바늘(미국 사이즈 6 또는 8)", ja: "針（米国サイズの6か8）", topic: "tackle-hooks" },
  { en: "Split shot", zh: "咬铅（夹在线上的小铅坠）", es: "Plomos partidos (split shot)", ko: "좁쌀봉돌", ja: "ガン玉", topic: "tackle-split-shot" },
  { en: "Worms or crickets", zh: "蚯蚓或蟋蟀", es: "Lombrices o grillos", ko: "지렁이나 귀뚜라미", ja: "ミミズかコオロギ", topic: "bait-worms" },
  { en: "Needle-nose pliers", zh: "尖嘴钳（摘钩用）", es: "Pinzas de punta", ko: "롱노즈 플라이어(바늘 빼기용)", ja: "ラジオペンチ（針外し用）", topic: "safe-handling" },
] as const;

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="trip-step">
      <span className="trip-step-n" aria-hidden="true">{n}</span>
      <div className="trip-step-body">
        <h2>{title}</h2>
        {children}
      </div>
    </li>
  );
}

/** Do I need a license? In one line where FishEye wrote the state's rules,
 * else the agency's own licence page. */
export function LicenseLine({ state }: { state: Jurisdiction | null }) {
  const t = useT().start;
  const locale = useLocale();
  if (!state) return <p>{t.pickState}</p>;
  const name = localStateName(state.code, state.name, locale);
  const age = state.license_from_age;
  if (age) {
    return (
      <>
        <p>{t.needFrom(name, age)}</p>
        <p className="trip-links">
          {state.license_url && (
            <a href={state.license_url} target="_blank" rel="noreferrer">
              {t.getLicense}
            </a>
          )}
          {state.license_topic && <Link href={`/fish#${state.license_topic}`}>{t.details}</Link>}
        </p>
      </>
    );
  }
  const agency = state.agency_short ?? state.agency ?? t.agencyOf(name);
  return state.license_url ? (
    <p>
      {t.agencySets(agency)}{" "}
      <a href={state.license_url} target="_blank" rel="noreferrer">
        {t.licensePage}
      </a>
    </p>
  ) : (
    <p>{t.checkAgency(agency)}</p>
  );
}

/** The kit as a checklist, and as a card to hold up in a tackle shop: big
 * English for the clerk, the reader's language underneath. */
function Kit() {
  const t = useT().start;
  const locale = useLocale();
  const [shopping, setShopping] = useState(false);
  // Ticked off in the shop; this page only, not kept.
  const [got, setGot] = useState<Set<string>>(() => new Set());
  const toggle = (topic: string) =>
    setGot((had) => {
      const next = new Set(had);
      if (!next.delete(topic)) next.add(topic);
      return next;
    });
  return (
    <>
      <ul className="trip-kit">
        {KIT.map((item) => (
          <li key={item.topic}>
            <input type="checkbox" checked={got.has(item.topic)} onChange={() => toggle(item.topic)} aria-label={t.got(locale === "en" ? item.en : item[locale])} />
            <span>
              <Link href={`/fish#${item.topic}`}>{locale === "en" ? item.en : item[locale]}</Link>
              {locale !== "en" && <span className="name-en" lang="en">{item.en}</span>}
            </span>
          </li>
        ))}
      </ul>
      <p className="trip-links">
        <button type="button" className="link-btn" onClick={() => setShopping(true)}>
          {t.showAtShop}
        </button>
      </p>
      <Modal open={shopping} onClose={() => setShopping(false)} title={t.shoppingList}>
        {/* English first and large: it's for the clerk to read. */}
        <ul className="shop-list" lang="en">
          {KIT.map((item) => (
            <li key={item.topic}>
              {item.en}
              {locale !== "en" && <span lang={locale}>{item[locale]}</span>}
            </li>
          ))}
        </ul>
      </Modal>
    </>
  );
}

type Nearby = { lake: WaterbodyListItem; km: number };

// Within a short drive; the map has everything further out.
const NEARBY_KM = 40;

/** The three official lakes open to the public nearest the person: places
 * FishEye can say something true about, with a public way in. */
function NearbySpots() {
  const all = useT();
  const t = all.start;
  const [state, setState] = useState<"idle" | "finding" | "done" | "failed">("idle");
  const [spots, setSpots] = useState<Nearby[]>([]);

  function find() {
    if (!navigator.geolocation) {
      setState("failed");
      return;
    }
    setState("finding");
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        const here = { latitude: coords.latitude, longitude: coords.longitude };
        try {
          const lakes = await listWaterbodies({
            lat: here.latitude,
            lng: here.longitude,
            radiusKm: NEARBY_KM,
            tier: "verified",
            limit: 100,
          });
          setSpots(
            lakes
              .filter((l) => l.public_access_status === "open")
              .map((lake) => ({ lake, km: kmApart(here, lake) }))
              .sort((a, b) => a.km - b.km)
              .slice(0, 3),
          );
          setState("done");
        } catch {
          setState("failed");
        }
      },
      () => setState("failed"),
      { timeout: 15_000, maximumAge: 300_000 },
    );
  }

  if (state === "done" && spots.length > 0) {
    return (
      <ul className="trip-spots">
        {spots.map(({ lake, km }) => (
          <li key={lake.id}>
            <Link href={`/map?lake=${lake.id}`}>{lake.name}</Link>
            <span className="muted">{all.common.miles(milesNumber(km))}</span>
          </li>
        ))}
      </ul>
    );
  }
  return (
    <>
      {state === "done" && <p>{t.noSpots}</p>}
      {state === "failed" && <p>{t.noLocation}</p>}
      <p className="trip-links">
        {state !== "done" && state !== "failed" && (
          <button type="button" className="btn btn-primary btn-sm" onClick={find} disabled={state === "finding"}>
            {state === "finding" ? t.finding : t.findSpots}
          </button>
        )}
        <Link href="/map">{t.openMap}</Link>
      </p>
    </>
  );
}

/** Line, bobber, split shot, hook and worm, top to bottom. */
function BobberRig() {
  const t = useT().start;
  return (
    <svg className="trip-rig" viewBox="0 0 220 170" role="img" aria-label={t.rigLabel}>
      <path d="M0 52c15-5 30 5 45 0s30-5 45 0 30 5 45 0 30-5 45 0 30 5 40 0" stroke="#8fb8b6" strokeWidth="2" fill="none" />
      <path d="M60 0v132" stroke="#5b6b63" strokeWidth="1.2" />
      <circle cx="60" cy="48" r="11" fill="#fff" stroke="#5b6b63" />
      <path d="M49 48a11 11 0 0 1 22 0z" fill="#d9534f" />
      <circle cx="60" cy="108" r="4" fill="#5b6b63" />
      <path d="M60 132v10a8 8 0 0 0 16 0v-4" stroke="#5b6b63" strokeWidth="1.6" fill="none" />
      <path d="M70 142c6 6 10-6 16 0s10-6 16 0" stroke="#c97a8a" strokeWidth="4" strokeLinecap="round" fill="none" />
      <g fill="#4b6157" fontSize="12" fontFamily="inherit">
        <text x="84" y="44">{t.rigBobber}</text>
        <text x="84" y="112">{t.rigShot}</text>
        <text x="112" y="150">{t.rigHook}</text>
      </g>
    </svg>
  );
}

export function FirstTrip() {
  const code = useSelectedState();
  const states = useJurisdictions();
  const state = code ? (states?.find((s) => s.code === code) ?? null) : null;
  const limitsUrl = state?.limits_url;
  const t = useT().start;

  return (
    <main className="page-scroll first-trip">
      <section className="page-intro">
        <p className="eyebrow">{t.eyebrow}</p>
        <h1>{t.title}</h1>
        <StatePicker />
      </section>
      <ol className="trip-steps">
        <Step n={1} title={t.step1}>
          <LicenseLine state={state} />
        </Step>
        <Step n={2} title={t.step2}>
          <Kit />
        </Step>
        <Step n={3} title={t.step3}>
          <p>{t.spotIntro}</p>
          <NearbySpots />
        </Step>
        <Step n={4} title={t.step4}>
          <BobberRig />
          <ul className="trip-tips">
            <li>
              {t.tieWith}<Link href="/fish#knot-improved-clinch">{t.knot}</Link>{t.tieEnd}
            </li>
            <li>
              {t.castAlong}<Link href="/fish#technique-shore">{t.cover}</Link>{t.castEnd}
            </li>
            <li>{t.whenDips}</li>
          </ul>
        </Step>
        <Step n={5} title={t.step5}>
          <ul className="trip-tips">
            <li>
              {t.wetHands}<Link href="/fish#care-release">{t.unhook}</Link>{t.unhookEnd}
            </li>
            <li>
              {t.keeping}
              {limitsUrl ? (
                <a href={limitsUrl} target="_blank" rel="noreferrer">
                  {t.limit} ↗
                </a>
              ) : (
                t.limit
              )}
              {t.first}
            </li>
            <li>
              {t.notSure} <Link href="/identify">{t.photoId}</Link>
            </li>
          </ul>
        </Step>
      </ol>
      <p className="trip-ask muted">
        {t.stuck} <Link href="/ask">{t.ask}</Link>
      </p>
    </main>
  );
}
