# Direct Company Career Feed Integration

How CareerOS stays current from **official company career sources** — employer careers sites and the
public job-board APIs they use — without depending on LinkedIn, Indeed or aggregators, and without
anyone copying vacancies by hand.

```
OFFICIAL CAREER SOURCE → SOURCE ADAPTER → FETCH / SYNC → STRUCTURED EXTRACTION → VALIDATION
→ DEDUPLICATION → CHANGE DETECTION → CAREEROS DATABASE → ADMIN / PUBLISHING POLICY → MOBILE APP
```

This extends the live discovery engine (DISCOVERY_ENGINE.md); it is not a second system. The per-company
audit is in [docs/career_sources.md](docs/career_sources.md).

## 1. Architecture map

| | |
|---|---|
| **Existing, reused** | Source registry (`content_sources`), discovery queue (`discovered_items`), runs (`discovery_runs`), change history (`content_changes`), adapters (Lever, Greenhouse, Ashby, SmartRecruiters, Workday, RSS, structured pages), the SSRF-safe HTTP client with robots.txt / rate limiting / size caps, the pipeline (company matching, dedup, change detection, removal detection), re-verification, the APScheduler dispatcher with its PostgreSQL leader lock, conditional run claiming, admin Sources/Discovery pages, public job API and mobile feeds (availability, provenance, internships, graduate programmes), audit log, follower notifications, logo capture. |
| **Was missing** | A starter company pack and importer; audit fields per source (job-search URL, ATS provider, readiness, last HTTP status, items last found); Oracle Recruiting support; Workday country scoping; microdata and sitemap reading for official pages; per-source country scope; confirmation before a vanished listing counts as removed; an auto-draft fast path; Test connection and health labels; trainee programme / apprenticeship types; region filtering; job function; a verification label. |
| **Changed** | Extended the models (migration `d8e2f4a6b7c9`), adapters, pipeline, registry API, jobs API, admin Sources/Discovery pages and the mobile job UI. Nothing was duplicated. |

## 2. Source types and readiness

The spec's source vocabulary maps onto the existing `SourceType` values; `ats_provider` records the
platform behind an official careers site.

| Spec name | Stored as |
|---|---|
| OFFICIAL_COMPANY_CAREERS, HTML_OFFICIAL | `OFFICIAL_CAREER_PAGE` (+ `discovery_method=STRUCTURED_DATA`) |
| OFFICIAL_ATS, GREENHOUSE, LEVER, ASHBY, SMARTRECRUITERS, WORKDAY, SUCCESSFACTORS | same-named `SourceType` |
| ORACLE_RECRUITING | `ORACLE` (`ats_provider=ORACLE_RECRUITING`) |
| RSS | `RSS` / `discovery_method=RSS` |
| MANUAL | `discovery_method=MANUAL` — never fetched |
| CUSTOM_STRUCTURED_API | not implemented (see §12) |
| NEWSROOM_SOURCE, INVESTOR_RELATIONS_SOURCE | `OFFICIAL_NEWSROOM`, `INVESTOR_RELATIONS` with content type `INTELLIGENCE` (separate parsers from jobs) |

**Readiness** (`content_sources.readiness`): `READY_STRUCTURED` (public ATS/API verified live),
`READY_HTML` (official pages with schema.org data verified live), `REQUIRES_CONFIGURATION` (route found but
something is missing, e.g. a site number), `MANUAL_ONLY`, `BLOCKED` (robots.txt, HTTP 403 or login walls —
never worked around), `UNVERIFIED`. Only `READY_*` sources are polled.

Registry field mapping: `career_base_url`→`url`, `job_search_url`, `ats_provider`, `country_scope`→`country`
+ `adapter_config_json.country_filter`, `region_scope`→`region`, `active`→`is_active`, `polling_enabled`,
`poll_interval_minutes`→`crawl_interval_minutes`, `last_checked_at`, `last_successful_sync_at`→`last_successful_fetch_at`,
`last_failure_at/reason`→`last_error_at/last_error`, `last_http_status`, `items_last_found`, `auto_publish_allowed`,
`requires_review` (computed: not auto-publish), `auto_create_draft`, `adapter_name` (resolved from type/method),
`parser_config_json`→`adapter_config_json`.

## 3. Adapter architecture

One adapter per **provider**, configured per employer through the registry — no company-specific code.
`SourceAdapter` (app/ingestion/adapters/base.py) exposes `validate_source()`, `fetch_jobs()`/`discover()`,
`health_check()`; normalization and detail fetches are provider-internal; external id and canonical URL
live on the validated record; job-status checks are the re-verification job.

| Adapter | Route | Scoping | Live verified (2026-09-15) |
|---|---|---|---|
| Greenhouse | Job board API; boards too large to return with descriptions fall back to the list + detail per new in-scope role | post-filter (out-of-scope roles skipped before the item cap, still counted as listed) | Moniepoint, Stripe, Cloudflare |
| Lever, Ashby | public posting APIs | post-filter | earlier discovery work (DISCOVERY_ENGINE.md) |
| **Workday** | `/wday/cxs/{tenant}/{site}/jobs` + detail | the tenant's own country facet, server-side; tenants without one are paged (bounded) and filtered | Unilever, Accenture, ABB, P&G, Rockwell, Adobe, Cisco, GE Vernova, Johnson Controls, NVIDIA, Toyota, Deloitte Ireland |
| **Oracle Recruiting Cloud** (new) | Candidate Experience REST (`recruitingCEJobRequisitions`, `…Details`) | the site's location facets, one request per country | MTN, TotalEnergies, Emerson, Honeywell, Oracle, FirstBank |
| **Official pages** | schema.org JobPosting as JSON-LD **or microdata**, from explicit pages, listing pages (`listing_pages` + `job_link_contains`) or sitemaps (`sitemap_urls`, newest first, `link_filters`) | post-filter | EY and SAP (SuccessFactors microdata), Chevron and Caterpillar (JSON-LD), Renaissance (Flair) |
| SmartRecruiters | public API | — | disallowed by robots.txt → off |
| RSS / newsroom | feeds | significance filter | DISCOVERY_ENGINE.md |

Structured data is always preferred; no browser automation; AI (off by default) is only a fallback for
pages without structured data and its output is validated like everything else.

**Detail budgets.** Workday, Oracle and large Greenhouse boards spend detail requests on postings CareerOS
hasn't seen (`SourceSnapshot.known_external_ids`). A known posting without a fresh detail fetch is a
*partial record*: it confirms the listing is still live but never overwrites stored facts or produces
change noise.

## 4. Seed registry

`backend/app/seeds/career_sources.json` — data, not code — holds the audited starter pack (74 sources across
Nigeria/Africa, energy, technology, engineering, FMCG and consulting). Import with
`python -m scripts.import_career_sources [--dry-run]` or **Sources → Import starter pack** (admins; shows a
dry-run preview). Idempotent: companies matched by name (created with only the stated fields), sources by
URL; re-imports refresh audit metadata and scope but never override an admin's operational choices
(active, polling, trust, auto-publish, auto-draft). Adding a company later is a registry entry, not a deploy.

## 5. Sync model

- **Scheduling.** The existing APScheduler instance runs the discovery dispatcher every 5 minutes: due
  sources (`polling_enabled`, `crawl_interval_minutes`, backoff) are enqueued as `discovery_runs`. Defaults:
  official career sources 6h, very large boards 12h, boards scanned without a country facet 24h.
- **Multi-instance safety.** The scheduler holds a PostgreSQL advisory leader lock; runs are claimed with a
  conditional update, and an open run for a source is reused, so replicas never ingest twice.
- **Failure isolation.** Each source is its own run; one failing source never stops others. Failures back
  off exponentially (429 honours `Retry-After`, capped at 24h); a run stuck for an hour is marked lost.
- **Run now.** `POST /admin/sources/{id}/run` returns 202 immediately; results appear in run history and the queue.
- **Test connection.** `POST /admin/sources/{id}/test`: at most 15 requests and 5 listings, nothing stored.
- **Health.** `HEALTHY` / `DEGRADED` (recent failure, partial or rate-limited run) / `FAILING` (3+ consecutive
  failures) / `PAUSED` / `UNKNOWN` (never checked).

## 6. Normalization, classification, location

Records are validated Pydantic models (`app/ingestion/schemas.py`); only stated facts are kept (no
invented salary, deadline, work mode or requirements). Jobs gain `job_function` (department / job family).
Classification uses explicit title markers or the source's own employment type: `GRADUATE_PROGRAM`,
`TRAINEE_PROGRAM` ("Management Trainee Programme"), `APPRENTICESHIP`, `INTERNSHIP`, otherwise `JOB`; any
experienced-hire marker keeps it a `JOB`. Trainee programmes appear in the Graduate Programs feed and
apprenticeships in Internships. Locations keep the raw source string (`location`) and derive `city`,
`state_or_region`, `country` only when a country is recognised (ISO codes, names, aliases; postcodes
dropped); multi-place listings get a country only when every place shares it.

## 7. Deduplication, change detection, closure, expiry

- **Dedup.** Strong keys: external id per source, requisition id, canonical URL; secondary: company + normalised
  title + location. A listing seen again updates the same item — never a new opportunity per sync.
- **Changes.** Tracked fields (title, deadline, description, requirements, location, application URL) on
  published records become pending `content_changes` with old/new values, source and time; editors apply or
  dismiss. History is never deleted.
- **Closure.** A listing absent from a *complete* source listing is `POSSIBLY_REMOVED` (still listed, flagged)
  until it has been missing for `DISCOVERY_REMOVAL_CONFIRMATIONS` consecutive complete syncs (default 2;
  per source `removal_confirmations`), then `SOURCE_REMOVED` — hidden from feeds and pending admin
  confirmation to expire. Reappearing restores `ACTIVE`. A source returning nothing while several listings
  were active skips removal detection that run. Partial scans (page limits, first results pages) never
  count as complete; listing pages are complete only with `listing_complete: true`.
- **Expiry.** A passed stated deadline marks the listing `DEADLINE_PASSED`/expired; details stay reachable for
  users who saved, analysed or tracked it. Re-verification (12h) re-checks published URLs.

## 8. Publishing policy

`SOURCE_AUTO_PUBLISH_ENABLED=false` by default. Flow: official source → queue → admin review → publish.
`auto_create_draft` (per source) prepares a DRAFT for each new verified vacancy with a matched company; an
editor still publishes. Auto-publish requires the global flag **and** the source's `auto_publish_allowed`,
trust ≥ 4, admin-verified ownership, a source-verified item, no flags and a matched company.

## 9. Admin

- **Sources:** readiness and health, ATS/adapter, last sync/HTTP status/listings in scope, last failure and
  backoff, items discovered/to review/published, scope; actions Run sync now, Test connection, Edit
  (schedule, auto-drafts, scope, listing pages, readiness), Enable/Disable, Runs, Items; filters; starter-pack import.
- **Discovery queue:** type tabs (including trainee programmes and apprenticeships), company, title, type,
  location/country, external job id, source and source type, posted and first-discovered dates, deadline,
  verification, duplicate/update/change status, missed syncs; actions Review, Create draft, Publish (from
  review), Ignore, Reject, View original. Metrics: healthy/failed sources, last sync, new/updated/duplicates,
  awaiting review, possibly removed, expired, live jobs by country and by industry.

## 10. App integration

Published imports are ordinary jobs referencing `company_id`, so company logos/industry changes show
without editing jobs. They appear in Home, Opportunities (Jobs, Internships, Graduate Programs), company
pages, search, saved items and recommendations. The jobs API filters by `country` (a country **or a region**
such as `Africa`), `industry` (job or company), `job_function`, experience level, work mode, employment type,
opportunity type and date posted; search covers title, company, location, country, skills, function and
company industry. Details carry `verification_status` (`OFFICIAL_ATS`, `OFFICIAL_SOURCE`, `VERIFIED`,
`UNVERIFIED`, `STALE` when not re-confirmed for 7 days, `SOURCE_REMOVED`); the app shows "Last checked"
rather than "verified" for stale listings. **Apply on official site** always opens the employer's own
application URL. ATS analysis uses the stored job; tracked applications keep working after a job closes.
Followers of a company are notified through the existing push infrastructure when a job is published.

## 11. Security and compliance

External content is untrusted: SSRF checks on every hop (no private, loopback or metadata addresses),
robots.txt honoured (unreachable robots fails closed), response size caps, defusedxml for feeds and
sitemaps, HTML reduced to text, validated URLs, no cookies or credentials, identifiable user agent,
per-host pacing and request budgets, prompt-injection defences for the optional AI path. Adapter config
accepts public identifiers only. Logs record host, status, size, duration and counts — never headers,
cookies, tokens or page bodies. Only factual job data and source links are stored.

**Flags:** `CAREER_SOURCE_SYNC_ENABLED` (alias `WEB_DISCOVERY_ENABLED`), `STRUCTURED_ATS_SYNC_ENABLED`,
`HTML_SOURCE_SYNC_ENABLED`, `AI_EXTRACTION_ENABLED` (alias `AI_RESEARCH_ENABLED`, default off),
`SOURCE_AUTO_PUBLISH_ENABLED` (alias `AUTO_PUBLISH_DISCOVERY`, default off), per-adapter flags
(`WORKDAY_DISCOVERY_ENABLED`, `ORACLE_RECRUITING_DISCOVERY_ENABLED`, …), `DISCOVERY_REMOVAL_CONFIRMATIONS`,
`OUTBOUND_TLS_TRUST_STORE`. Per-source overrides: polling, schedule, scope, auto-draft, auto-publish.

## 12. Verification status and known limitations

- **Tests (mocked, repeatable):** adapters for every provider including Workday facets/detail budgets, Oracle
  facets/external-only fields, Greenhouse large-board fallback, microdata, sitemaps, listing completeness;
  pipeline new/duplicate/update/removal-confirmation/reappearance; seed idempotency; health; Test
  connection; auto-drafts; country scope; region/function filters; verification labels; company logo
  relationship; metrics; migration upgrade/downgrade/check on a clean database.
- **Live (2026-09-15):** every READY source synced once through the production pipeline into a local dev
  database (docs/career_sources.md); 15 Nigeria-based roles (MTN, EY, SAP) were then published through the
  review service and served by the public API. Defects this surfaced were fixed and covered by tests.
- **Not verified:** long-running scheduled polling in production; PostgreSQL migration run; the full
  mobile flow on a device for these imports (the emulator session had expired); push notifications (mock
  provider).
- **Limitations:** 25 starter sources need configuration and 23 are manual-only or blocked — including
  Shell, bp, Microsoft, Nestlé, Seplat and several Nigerian banks. Workday tenants without a country facet
  and first-page-only listings are partial scans. No adapter yet for custom JSON APIs (e.g. amazon.jobs),
  iCIMS, Eightfold, Phenom or Avature. No `NEW_INTERNSHIP` / `MATCHING_OPPORTUNITY` notifications beyond
  followed-company alerts.
