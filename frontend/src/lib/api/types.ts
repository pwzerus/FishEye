// Mirrors backend/app/schemas/waterbody.py. Kept hand-in-sync for now —
// see the note in README about generating this from the OpenAPI schema
// once the API surface stabilizes (Day 3+), rather than doing that up
// front for a schema that's still moving daily.

export interface WaterbodyListItem {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  field_tested: boolean;
  // "open" | "closed" — whether the lake itself is open to public access
  // at all, independent of any one AccessPoint's own public_status. See
  // backend/app/models/waterbody.py — added after TPWD's own access page
  // for Gibbons Creek Reservoir showed it closed to the public since
  // 12/25/21.
  // "unknown" for lakes from the statewide OpenStreetMap layer: the map
  // knows the lake exists, not whether it's open.
  public_access_status: PublicAccessStatus;
  data_tier: DataTier;
  // From OpenStreetMap's water=* tag; null for hand-curated lakes.
  water_type: WaterType | null;
  // Distinct species with outside records (GBIF) here. See ReportedSpecies.
  reported_species_count: number;
}

export type WaterType = "lake" | "reservoir" | "pond";

// "verified": hand-curated or from an official source (TPWD) — species,
//   confirmed-public access, scoring and AI explanations all apply.
// "osm": imported from OpenStreetMap to show that a lake exists at all.
//   Community-mapped, no species, entrances are "osm_reported" and never
//   scored. See backend/app/models/waterbody.py and ADR 0010.
export type DataTier = "verified" | "osm";
export type PublicAccessStatus = "open" | "closed" | "unknown";

// Mirrors backend/app/schemas/geocoding.py.
export interface GeocodeResult {
  query: string;
  display_name: string;
  latitude: number;
  longitude: number;
}

export interface AccessPoint {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  access_type: string;
  public_status: string;
  parking: boolean;
}

export interface SpeciesSummary {
  common_name: string;
  difficulty: string;
  confidence: string;
  evidence: string;
  source_url: string;
  observed_at: string;
}

// Mirrors ReportedSpeciesOut in backend/app/schemas/waterbody.py. A species
// someone has recorded at this lake (GBIF: museum collections, surveys,
// iNaturalist). Evidence it has been found here, NOT an official
// confirmation: never shown as confirmed, never scored, never given to the
// AI advisor. See docs/adr/0012-gbif-reported-species.md.
export interface ReportedSource {
  name: string;
  records: number;
}

export interface ReportedSpecies {
  common_name: string;
  records: number;
  last_year: number | null;
  sources: ReportedSource[];
  latest_record_url: string | null;
  // A single record from before 2000, or undated.
  weak: boolean;
  // Also on this lake's official species list.
  also_confirmed: boolean;
}

export interface WaterbodyDetail {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  access_summary: string;
  source_url: string;
  source_updated_at: string;
  field_tested: boolean;
  public_access_status: PublicAccessStatus;
  data_tier: DataTier;
  water_type: WaterType | null;
  access_points: AccessPoint[];
  species: SpeciesSummary[];
  reported_species: ReportedSpecies[];
}

// Mirrors backend/app/schemas/admin.py.
export type JobStatus = "idle" | "running" | "done" | "error";

export interface RefreshTrigger {
  status: JobStatus;
  message: string;
}

export interface LakeResultOut {
  name: string;
  status: string;
  species_written: number;
  access_points_written: number;
  detail: string;
}

export interface RefreshStatus {
  status: JobStatus;
  started_at: string | null;
  finished_at: string | null;
  total_written: number | null;
  total_access_points_written: number | null;
  dry_run: boolean | null;
  lake_results: LakeResultOut[] | null;
  error: string | null;
}

// Mirrors backend/app/schemas/weather.py.
export interface CurrentConditions {
  temperature: number | null;
  temperature_unit: string;
  wind_speed: string | null;
  wind_direction: string | null;
  short_forecast: string;
  is_daytime: boolean;
}

export interface HourlyPeriod {
  start_time: string;
  temperature: number | null;
  temperature_unit: string;
  wind_speed: string | null;
  wind_direction: string | null;
  short_forecast: string;
  probability_of_precipitation: number | null;
}

export interface WeatherAlert {
  event: string;
  severity: string;
  headline: string | null;
  effective: string | null;
  expires: string | null;
}

// `source` distinguishes live NWS data from the fixed-template fallback
// used when NWS is unreachable (backend/app/services/weather_adapter.py).
// A UI must not present fallback values (all null/empty) as real readings.
export type WeatherSource = "nws" | "fallback";

export interface Weather {
  latitude: number;
  longitude: number;
  current: CurrentConditions;
  hourly: HourlyPeriod[];
  alerts: WeatherAlert[];
  source: WeatherSource;
  stale: boolean;
  fetched_at: string;
}

// Mirrors backend/app/schemas/recommendation.py.
export interface RecommendationRequest {
  waterbody_id: number;
  target_species?: string;
  limit?: number;
}

export interface Factor {
  name: string;
  weight: number;
  // null means "no data for this factor" — excluded from the score and
  // deducted from confidence, never silently scored as zero. See
  // backend/app/services/scoring.py.
  value: number | null;
  reason: string;
}

export interface SpotCandidate {
  access_point_id: number;
  name: string;
  latitude: number;
  longitude: number;
  access_type: string;
  public_access_status: string;
  score: number;
  confidence: number;
  factors: Factor[];
  missing_signals: string[];
}

export interface TimeWindow {
  start_time: string;
  end_time: string;
  reason: string;
}

export interface WeatherWarning {
  event: string;
  severity: string;
  headline: string | null;
}

// Mirrors backend/app/schemas/advisor.py.
export interface AdvisorRequest {
  waterbody_id: number;
  target_species?: string;
  limit?: number;
}

export interface AdvisorSource {
  url: string;
  label: string;
}

/**
 * The model-authored part of an advisor response — and the ONLY
 * model-authored part. Note what's missing: no confidence, no coordinates,
 * no species determination, no regulations. Those are the four things the
 * backend never lets a model decide, so there's no field here to carry
 * them (see docs/adr/0007-ai-advisor-grounding.md).
 */
export interface AdvisorExplanation {
  summary: string;
  gear: string[];
  bait: string[];
  steps: string[];
  risks: string[];
  sources: AdvisorSource[];
}

export interface AdvisorTrace {
  trace_id: string;
  provider: string;
  model: string;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost_usd: number;
  validation_attempts: number;
  // "ok" | "invalid_json" | "ungrounded_source" | "ungrounded_species"
  //   | "provider_unavailable"
  outcome: string;
  retrieved_source_count: number;
  cache_hit: boolean;
}

export interface AdvisorResponse {
  waterbody_id: number;
  waterbody_name: string;
  target_species: string | null;
  explanation: AdvisorExplanation;
  // "llm" when the model's output passed the backend's grounding checks,
  // "fallback" when the fixed template was used instead. A UI that ignores
  // this will eventually present one as the other.
  answer_source: "llm" | "fallback";
  // Server-computed, never model output.
  confidence: number;
  safety_warnings: WeatherWarning[];
  best_time_window: TimeWindow | null;
  candidates: SpotCandidate[];
  weather_source: WeatherSource;
  trace: AdvisorTrace;
  generated_at: string;
}

export interface RecommendationResponse {
  waterbody_id: number;
  waterbody_name: string;
  target_species: string | null;
  candidates: SpotCandidate[];
  best_time_window: TimeWindow | null;
  // Top-level, not per-candidate: severe-weather warnings must take
  // priority over the ranking itself (PRD §17), so a caller can't render
  // the candidate list without also having these in hand.
  safety_warnings: WeatherWarning[];
  weather_source: WeatherSource;
  generated_at: string;
}

// Mirrors backend/app/schemas/species_guide.py.
export interface GuideSource {
  label: string;
  url: string;
  // "guide" = a fishing guide's or tackle site, not an agency or established
  // publication; the UI labels it so a reader can weigh it accordingly.
  kind: "agency" | "publication" | "guide";
}

export interface TackleSetup {
  name: string;
  use_when: string;
  rod: string;
  reel: string;
  line: string;
  terminal: string;
  sources: GuideSource[];
}

export interface SpeciesGuide {
  slug: string;
  common_name: string;
  scientific_name: string;
  role: "sport" | "forage";
  difficulty: "beginner" | "intermediate" | "advanced" | null;
  summary: string;
  diet: string;
  where_and_when: string[];
  live_baits: string[];
  lures: string[];
  setups: TackleSetup[];
  tips: string[];
  identification: string[];
  how_to_get: string[];
  bait_for: string[];
  legal_notes: string[];
  limits_url: string;
  sources: GuideSource[];
}
