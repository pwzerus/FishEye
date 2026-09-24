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
  public_access_status: "open" | "closed";
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

export interface WaterbodyDetail {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  access_summary: string;
  source_url: string;
  source_updated_at: string;
  field_tested: boolean;
  public_access_status: "open" | "closed";
  access_points: AccessPoint[];
  species: SpeciesSummary[];
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
