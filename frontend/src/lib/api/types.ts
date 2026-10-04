// Mirrors backend/app/schemas/waterbody.py. Kept hand-in-sync for now —
// see the note in README about generating this from the OpenAPI schema
// once the API surface stabilizes (Day 3+), rather than doing that up
// front for a schema that's still moving daily.

/** GET /api/states — a state FishEye has a row for, and whether any lake in
 * it is on file (the national map lights those and greys the rest). */
export interface StateCoverage {
  id: number;
  name: string;
  code: string;
  official_source_url: string;
  has_waterbodies: boolean;
}

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
  // ISO with the lake's own UTC offset ("…T18:00:00-05:00"): lake time.
  start_time: string;
  end_time: string;
  reason: string;
  label?: "morning" | "evening" | null;
  score?: number | null;
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
  bite_windows?: TimeWindow[];
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
  // The morning and the evening bite, each its own best 3-hour block, in
  // time order. Empty when the forecast isn't live.
  bite_windows?: TimeWindow[];
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
  // Which group this setup belongs in on the page: artificial lure, live
  // or natural bait, or either (some setups explicitly name both).
  method: "lure" | "bait" | "either";
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
  diet_type: "carnivore" | "omnivore" | "filter_feeder";
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

// GET /api/species/photos (backend app/services/species_photos.py).
// A real, freely licensed photo; `author` and `license` must be shown with it.
export interface SpeciesPhoto {
  url: string;
  width: number;
  height: number;
  author: string;
  license: string;
  license_url: string | null;
  file_page: string;
  source: string;
}

export type SpeciesPhotos = Record<string, SpeciesPhoto | null>;

// POST /api/ask (backend app/services/rag/ask.py).
export interface AskRequest {
  question: string;
  species_slug?: string | null;
}

export interface AskCitation {
  id: string; // "<species-slug>#<section>"
  species_slug: string;
  species_name: string; // "" for passages that apply to every fish
  section: string; // "diet", "live_baits", "setup-2", ...
  title: string;
  excerpt: string;
  sources: GuideSource[];
}

export type AskAnswerSource = "llm" | "fallback" | "no_match";

export interface AskTrace {
  trace_id: string;
  retriever: string;
  routed_species: string[];
  retrieved: { id: string; score: number }[];
  provider: string;
  model: string;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost_usd: number;
  validation_attempts: number;
  outcome: string;
  cache_hit: boolean;
}

export interface AskResponse {
  question: string;
  answer: string;
  answer_source: AskAnswerSource;
  citations: AskCitation[];
  trace: AskTrace;
}

// ---------------------------------------------------------------------------
// Accounts and community pins (backend app/api/auth.py, pins.py,
// admin_community.py; docs/adr/0016-accounts-and-community-pins.md)

export interface User {
  id: number;
  email: string;
  display_name: string;
  role: "user" | "admin";
  status: "active" | "suspended";
  has_password: boolean;
  google_connected: boolean;
  created_at: string;
}

export interface AuthProviders {
  password: boolean;
  google: boolean;
}

export type PinVisibility = "public" | "private";
export type PinStatus = "published" | "hidden" | "removed";

export interface PinPhoto {
  id: number;
  url: string;
  thumb_url: string;
  width: number;
  height: number;
}

export interface PinSummary {
  id: number;
  latitude: number;
  longitude: number;
  title: string;
  species_slug: string | null;
  species_label: string | null;
  caught_on: string | null;
  created_at: string;
  visibility: PinVisibility;
  status: PinStatus;
  // "reports" (auto-hidden) | "moderator"
  status_reason: string | null;
  author: { id: number; display_name: string };
  lake: { id: number; name: string } | null;
  photo_count: number;
  thumb_url: string | null;
  is_mine: boolean;
}

export interface PinDetail extends PinSummary {
  note: string | null;
  photos: PinPhoto[];
  can_edit: boolean;
  can_report: boolean;
  reported_by_me: boolean;
}

export interface PinOptions {
  species: { slug: string; label: string }[];
  report_reasons: { id: string; label: string }[];
  max_photos: number;
  max_photo_mb: number;
}

export interface PinUpdate {
  title?: string;
  note?: string;
  species_slug?: string;
  species_other?: string;
  caught_on?: string;
  visibility?: PinVisibility;
  clear_note?: boolean;
  clear_species?: boolean;
  clear_caught_on?: boolean;
}

export interface AdminStats {
  users: number;
  users_new_7d: number;
  users_active_7d: number;
  admins: number;
  suspended: number;
  pins: number;
  pins_new_7d: number;
  pins_public: number;
  pins_private: number;
  pins_hidden: number;
  pins_removed: number;
  photos: number;
  open_reports: number;
  pins_awaiting_review: number;
}

export interface AdminReportGroup {
  pin: PinSummary;
  reports: { id: number; reason: string; reason_label: string; detail: string | null; reporter: string; created_at: string }[];
}

export interface AdminPin extends PinSummary {
  open_reports: number;
  author_email: string;
}

export interface AdminUser {
  id: number;
  email: string;
  display_name: string;
  role: "user" | "admin";
  status: "active" | "suspended";
  has_password: boolean;
  google_connected: boolean;
  created_at: string;
  last_login_at: string | null;
  pins: number;
  reports_against: number;
}

export interface AuditEntry {
  id: number;
  actor: string;
  action: string;
  target_type: string;
  target_id: number;
  detail: string | null;
  created_at: string;
}

export interface Paged<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}
