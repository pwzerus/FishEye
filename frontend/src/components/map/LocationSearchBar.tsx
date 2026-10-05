"use client";

import { useState } from "react";

import { ApiError, geocodePlace } from "@/lib/api/client";

export interface LocatedPoint {
  latitude: number;
  longitude: number;
  label: string;
}

/**
 * The address search box + "use my location" button, styled like a
 * familiar map app's search bar. Both paths end the same way — calling
 * onLocate with a point — so the map only has to know how to react to
 * "the user is now interested in this point", not which path got there.
 *
 * Neither path talks to a third-party geocoder directly: text search goes
 * through this app's own /api/geocode (see backend/app/services/geocoding.py
 * for why — Nominatim's usage policy doesn't allow many independent
 * browsers hitting its public endpoint), and "use my location" is the
 * browser's own Geolocation API, which needs no geocoding at all.
 */
export function LocationSearchBar({ onLocate }: { onLocate: (point: LocatedPoint) => void }) {
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 2) return;

    setSearching(true);
    setError(null);
    geocodePlace(trimmed)
      .then((result) => {
        onLocate({
          latitude: result.latitude,
          longitude: result.longitude,
          label: result.display_name,
        });
      })
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 404) {
          setError(`Couldn't find "${trimmed}". Try a city, lake name, or ZIP code.`);
        } else {
          setError("Location search is temporarily unavailable. Try again shortly.");
        }
      })
      .finally(() => setSearching(false));
  }

  function handleUseMyLocation() {
    if (!("geolocation" in navigator)) {
      setError("This browser doesn't support location access.");
      return;
    }
    setLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        onLocate({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          label: "Your location",
        });
      },
      (geoError) => {
        setLocating(false);
        // PERMISSION_DENIED (1) is the common case — the person said no
        // to the browser's own permission prompt, not a bug here.
        setError(
          geoError.code === geoError.PERMISSION_DENIED
            ? "Location access was denied. You can still search by name above."
            : "Couldn't get your location right now.",
        );
      },
      { enableHighAccuracy: false, timeout: 10_000 },
    );
  }

  return (
    <div className="location-search-bar">
      <form onSubmit={handleSubmit} className="location-search-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search a city, lake, or ZIP code"
          className="location-search-input"
          aria-label="Search for a location"
        />
        <button type="submit" className="location-search-button" disabled={searching}>
          {searching ? "Searching…" : "Search"}
        </button>
      </form>
      <button
        type="button"
        className="locate-me-button"
        onClick={handleUseMyLocation}
        disabled={locating}
        title="Use my current location"
      >
        {locating ? "Locating…" : "📍 Use my location"}
      </button>
      {error && <div className="location-search-error">{error}</div>}
    </div>
  );
}
