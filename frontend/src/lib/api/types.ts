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
  access_points: AccessPoint[];
  species: SpeciesSummary[];
}
