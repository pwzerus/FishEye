"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import type { WaterbodyListItem } from "@/lib/api/types";
import { WaterbodyPanel } from "@/components/waterbody/WaterbodyPanel";

// Leaflet touches `window` at import time, which breaks server-side
// rendering. next/dynamic with ssr:false has to be called from a client
// component (App Router forbids it from a server component directly) —
// this file is that boundary.
const LakeMap = dynamic(() => import("./LakeMap"), {
  ssr: false,
  loading: () => <div className="map-loading">Loading map…</div>,
});

export function MapView({ waterbodies }: { waterbodies: WaterbodyListItem[] }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);

  return (
    <div className="map-view">
      <div className="map-container">
        <LakeMap waterbodies={waterbodies} onSelect={setSelectedId} />
      </div>
      <aside className="side-panel">
        <WaterbodyPanel waterbodyId={selectedId} />
      </aside>
    </div>
  );
}
