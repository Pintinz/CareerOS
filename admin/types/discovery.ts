// Live discovery engine types — mirror backend/app/schemas/admin_ops.py (DISCOVERY_ENGINE.md).

export const SOURCE_TYPES = [
  "OFFICIAL_CAREER_PAGE", "OFFICIAL_NEWSROOM", "INVESTOR_RELATIONS", "GOVERNMENT", "REGULATOR", "UNIVERSITY",
  "SCHOLARSHIP_PROVIDER", "GREENHOUSE", "LEVER", "ASHBY", "SMARTRECRUITERS", "WORKDAY", "SUCCESSFACTORS", "ORACLE",
  "RSS", "INDUSTRY_PUBLICATION", "NEWS_MEDIA", "AGGREGATOR", "OTHER",
] as const;
export type SourceType = (typeof SOURCE_TYPES)[number];

export const CONTENT_TYPES = [
  "JOB", "INTERNSHIP", "GRADUATE_PROGRAM", "APPRENTICESHIP", "TRAINEE_PROGRAM", "SCHOLARSHIP", "FELLOWSHIP", "INTELLIGENCE",
] as const;
export type ContentType = (typeof CONTENT_TYPES)[number];

export const DISCOVERY_METHODS = ["STRUCTURED_API", "RSS", "STRUCTURED_DATA", "AI_RESEARCH", "MANUAL"] as const;
export type DiscoveryMethod = (typeof DISCOVERY_METHODS)[number];

export type RunStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "PARTIAL" | "FAILED" | "RATE_LIMITED" | "SKIPPED";

export const READINESS = ["READY_STRUCTURED", "READY_HTML", "REQUIRES_CONFIGURATION", "MANUAL_ONLY", "BLOCKED", "UNVERIFIED"] as const;
export type Readiness = (typeof READINESS)[number];
export const READINESS_LABELS: Record<Readiness, string> = {
  READY_STRUCTURED: "Ready · structured",
  READY_HTML: "Ready · official pages",
  REQUIRES_CONFIGURATION: "Needs configuration",
  MANUAL_ONLY: "Manual only",
  BLOCKED: "Blocked",
  UNVERIFIED: "Not audited",
};
export type SourceHealthLabel = "HEALTHY" | "DEGRADED" | "FAILING" | "PAUSED" | "UNKNOWN";

export interface SourceHealth {
  id: string;
  name: string;
  organization: string | null;
  url: string;
  domain: string | null;
  source_type: SourceType;
  country: string | null;
  region: string | null;
  industry: string | null;
  company_id: string | null;
  trust_level: number;
  discovery_method: DiscoveryMethod;
  content_types: ContentType[];
  adapter_config_json: Record<string, unknown>;
  is_active: boolean;
  polling_enabled: boolean;
  crawl_interval_minutes: number;
  auto_publish_allowed: boolean;
  verification_status: "UNVERIFIED" | "VERIFIED" | "FAILING";
  last_checked_at: string | null;
  last_successful_fetch_at: string | null;
  last_error: string | null;
  last_error_at: string | null;
  last_error_code: string | null;
  consecutive_failures: number;
  next_poll_after: string | null;
  job_search_url: string | null;
  ats_provider: string | null;
  readiness: Readiness;
  readiness_note: string | null;
  auto_create_draft: boolean;
  last_http_status: number | null;
  items_last_found: number | null;
  requires_review: boolean;
  created_at: string;
  items_discovered?: number;
  items_awaiting_review?: number;
  items_published?: number;
  last_run_status?: RunStatus | null;
  last_run_at?: string | null;
  adapter_available?: boolean;
  adapter_name?: string | null;
  company_name?: string | null;
  last_run_new?: number | null;
  last_run_updated?: number | null;
  last_run_duplicates?: number | null;
  last_run_removed?: number | null;
  health?: SourceHealthLabel;
}

export interface SourceTest {
  ok: boolean;
  adapter: string | null;
  found: number;
  complete: boolean;
  sample_titles: string[];
  warnings: string[];
  error_code: string | null;
  error: string | null;
  http_status: number | null;
  requests: number;
}

export interface SeedImport {
  dry_run: boolean;
  companies_created: number;
  sources_created: number;
  sources_updated: number;
  sources_unchanged: number;
}

export interface DiscoveryRun {
  id: string;
  source_id: string | null;
  run_type: "SOURCE_DISCOVERY" | "VERIFICATION";
  trigger: "SCHEDULED" | "MANUAL";
  status: RunStatus;
  queued_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  items_found: number;
  items_new: number;
  items_updated: number;
  items_duplicate: number;
  items_invalid: number;
  items_removed: number;
  error_code: string | null;
  error_message: string | null;
  stats_json: Record<string, unknown>;
}

export type ItemStatus =
  | "NEW" | "NEEDS_REVIEW" | "VERIFIED" | "DUPLICATE" | "IGNORED" | "REJECTED" | "DRAFT_CREATED" | "PUBLISHED" | "SOURCE_REMOVED" | "ERROR";

export interface DiscoveredItem {
  id: string;
  source_id: string;
  source_name: string | null;
  source_type: SourceType | null;
  item_type: ContentType;
  external_id: string | null;
  detected_title: string;
  detected_company_name: string | null;
  company_id: string | null;
  original_url: string;
  canonical_url: string | null;
  location: string | null;
  country: string | null;
  published_at: string | null;
  deadline: string | null;
  status: ItemStatus;
  verification_status: "UNVERIFIED" | "SOURCE_VERIFIED" | "EVIDENCE_MISMATCH" | "FETCH_FAILED" | "MANUAL_REVIEW_REQUIRED";
  trust_level: number | null;
  confidence: number | null;
  duplicate_of_id: string | null;
  matched_entity_type: string | null;
  matched_entity_id: string | null;
  created_draft_id: string | null;
  pending_changes: number;
  flags: string[];
  missing_runs: number;
  created_at: string;
  last_seen_at: string | null;
}

export interface ContentChange {
  id: string;
  entity_type: string;
  entity_id: string;
  field: string;
  old_value: unknown;
  new_value: unknown;
  source_id: string | null;
  discovered_item_id: string | null;
  status: "PENDING" | "APPLIED" | "DISMISSED";
  detected_at: string;
  resolved_at: string | null;
}

export interface DiscoveryEvidence {
  source_quality?: string;
  source_name?: string;
  source_type?: string;
  trust_level?: number;
  source_ownership_verified?: boolean;
  matched_organization?: { company_id: string; name: string; method: string } | null;
  proposed_company?: { name: string; website_url: string | null; career_url: string | null; industry: string | null; country: string | null } | null;
  external_id?: string | null;
  requisition_id?: string | null;
  discovery_method?: string;
  checks?: string[];
  flags?: string[];
  injection_suspected?: boolean;
  injection_markers?: string[];
  dedup?: string[];
  verified_at?: string;
  ai_provider?: string;
  ai_model?: string;
  page_truncated?: boolean;
  dropped_fields?: string[];
  auto_publish_blocked_by?: string[];
  [key: string]: unknown;
}

export interface DiscoveryReview {
  item: DiscoveredItem;
  source: SourceHealth;
  evidence: DiscoveryEvidence;
  extracted: Record<string, unknown>;
  raw_payload: Record<string, unknown>;
  current_record: Record<string, unknown> | null;
  pending_changes: ContentChange[];
  duplicate_of: DiscoveredItem | null;
  can_publish: boolean;
  publish_blockers: string[];
}

export interface DiscoveryMetrics {
  active_sources: number;
  polling_sources: number;
  failing_sources: number;
  discovery_runs_24h: number;
  failed_runs_24h: number;
  items_found_24h: number;
  items_verified: number;
  duplicates_24h: number;
  awaiting_review: number;
  pending_changes: number;
  opportunities_expired_7d: number;
  source_removed_pending: number;
  average_run_ms_24h: number | null;
  auto_publish_enabled: boolean;
  ai_research_available: boolean;
  flags: Record<string, boolean | number>;
  healthy_sources: number;
  sources_by_readiness: Record<string, number>;
  last_run_at: string | null;
  items_new_24h: number;
  items_updated_24h: number;
  possibly_removed: number;
  jobs_by_country: { country: string; count: number }[];
  jobs_by_industry: { industry: string; count: number }[];
}

export const CONTENT_TYPE_LABELS: Record<ContentType, string> = {
  JOB: "Job",
  INTERNSHIP: "Internship",
  GRADUATE_PROGRAM: "Graduate programme",
  APPRENTICESHIP: "Apprenticeship",
  TRAINEE_PROGRAM: "Trainee programme",
  SCHOLARSHIP: "Scholarship",
  FELLOWSHIP: "Fellowship",
  INTELLIGENCE: "Intelligence",
};

export function formatDate(value: string | null | undefined, withTime = false): string {
  if (!value) return "—";
  const date = new Date(value);
  return withTime
    ? date.toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function humanize(value: string | null | undefined): string {
  if (!value) return "—";
  const words = value.replace(/_/g, " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}
