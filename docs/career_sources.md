# Career sources — starter company audit

Audited live on 2026-09-15 with the production discovery client (robots.txt honoured, one small request per check,
about one request per second). Source of truth for the registry: `backend/app/seeds/career_sources.json`, imported with
`python -m scripts.import_career_sources` or **Sources → Import starter pack**. Design: `CAREER_SOURCE_INTEGRATION.md`.

- **Verification level.** "Live sync" counts are from a one-off sync of each ready source through the real pipeline on
  2026-09-15 (results went to the review queue). They are a snapshot, not a guarantee the site stays reachable.
- **Scope.** Ready sources default to `country_filter: ["AFRICA"]`; admins can widen or narrow it per source.
- **Nothing here is guessed.** An ATS is listed only when the official careers page links to it, and only endpoints that
  answered live are marked ready. Sites that refused automated access are recorded as blocked and tracked manually.

| Readiness | Sources |
|---|---|
| Ready — structured (public ATS / API) | 21 |
| Ready — official pages with structured data | 5 |
| Requires configuration | 25 |
| Manual only | 7 |
| Blocked (access refused; never worked around) | 16 |

## Ready — structured (public ATS / API)

| Company | Group | Official careers URL | ATS / route | Fetched endpoint | Sync | Live sync (2026-09-15) | Notes |
|---|---|---|---|---|---|---|---|
| Accenture | Consulting | https://www.accenture.com/us-en/careers | WORKDAY | https://accenture.wd103.myworkdayjobs.com/AccentureCareers | every 12h | 40 in Africa (country facet) | Workday site linked from the careers page; country facets (Egypt, South Africa listed when checked). |
| Deloitte | Consulting | https://www.deloitte.com/global/en/careers.html | WORKDAY | https://deloitteie.wd3.myworkdayjobs.com/Experienced_Professionals | off | 0 — Ireland member firm (not polled) | Deloitte hires per member firm; the global job search links Deloitte Ireland's Workday site. Other member firms (e.g. Nigeria) need their own sources. |
| Johnson Controls | Engineering / Industrial | https://jobs.johnsoncontrols.com/ | WORKDAY | https://jci.wd5.myworkdayjobs.com/JCI | every 24h | 0 in the newest 200 (no country facet; partial) | Workday site linked from the careers page. No country facet exposed: newest pages scanned and filtered (partial), so it syncs daily. |
| Rockwell Automation | Engineering / Industrial | https://www.rockwellautomation.com/en-us/careers.html | WORKDAY | https://rockwellautomation.wd1.myworkdayjobs.com/External_Rockwell_Automation | every 12h | 1 in Africa (country facet) | Workday site linked from the careers page; country facets (South Africa listed when checked). |
| Toyota | Engineering / Industrial | https://careers.toyota.com/us/en | WORKDAY | https://toyota.wd503.myworkdayjobs.com/TMNA | off | 0 — North America site (not polled) | Workday site for Toyota Motor North America only (US roles); verified but not polled for CareerOS's current markets. |
| P&G | FMCG / Manufacturing | https://www.pgcareers.com/mea/en | WORKDAY | https://pg.wd5.myworkdayjobs.com/1000 | every 12h | 23 in Africa (country facet) | Workday site linked from pgcareers.com; country facets (Egypt, Morocco, South Africa listed when checked). |
| Unilever | FMCG / Manufacturing | https://careers.unilever.com/en | WORKDAY | https://unilever.wd3.myworkdayjobs.com/Unilever_Experienced_Professionals | every 6h | 8 in Africa (country facet) | Workday site linked from careers.unilever.com; country facet scoping (Egypt, Kenya, South Africa listed when checked). |
| FirstBank | Nigeria / Africa | https://firstbankgroup.com/ng/home/careers/ | ORACLE_RECRUITING | https://hdbc.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX | every 12h | 0 — no open requisitions | Oracle Recruiting site CX linked from the careers page; no open requisitions when checked. |
| MTN | Nigeria / Africa | https://www.mtn.ng/career | ORACLE_RECRUITING | https://ehle.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1 | every 6h | 30 in Africa (Nigeria 10, Cameroon 10, South Africa 8, Uganda 2) | Oracle Recruiting site CX_1 linked from mtn.ng/career; covers several MTN operating companies, scoped by the site's country facets. |
| Moniepoint | Nigeria / Africa | https://moniepoint.com/careers | GREENHOUSE | https://boards.greenhouse.io/moniepoint | every 6h | 203 listings (no country scope) | Public Greenhouse board API; ~200 openings, mostly Nigeria. |
| ABB | Oil, Gas & Energy | https://careers.abb/global/en | WORKDAY | https://abb.wd3.myworkdayjobs.com/External_Career_Page | every 12h | 17 in Africa (country facet) | Workday site linked from the Phenom-hosted search page; country facets (Egypt, South Africa listed when checked). |
| Emerson | Oil, Gas & Energy | https://www.emerson.com/en/corporate/careers | ORACLE_RECRUITING | https://hdjq.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1 | every 12h | 0 in Africa | Oracle Recruiting site CX_1 linked from the careers page. |
| GE Vernova | Oil, Gas & Energy | https://careers.gevernova.com/ | WORKDAY | https://gevernova.wd5.myworkdayjobs.com/Vernova_ExternalSite | every 24h | 0 in the newest 200 (no country facet; partial) | Workday site linked from the careers page. No country facet exposed: the newest pages are scanned and filtered after fetching (partial), so it syncs daily. |
| Honeywell | Oil, Gas & Energy | https://careers.honeywell.com/en/sites/Honeywell | ORACLE_RECRUITING | https://ibqbjb.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/Honeywell | every 12h | 0 in Africa | Oracle Recruiting site 'Honeywell' behind careers.honeywell.com. |
| TotalEnergies | Oil, Gas & Energy | https://jobs.totalenergies.com/ | ORACLE_RECRUITING | https://fa-eocc-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX | every 6h | 60 in Africa | Oracle Recruiting site CX linked from the job search page. |
| Adobe | Technology | https://careers.adobe.com/us/en | WORKDAY | https://adobe.wd5.myworkdayjobs.com/external_experienced | every 12h | 0 — no African country in the site's facets | Workday site (experienced roles) linked from the Phenom-hosted search page. |
| Cisco | Technology | https://careers.cisco.com/global/en | WORKDAY | https://cisco.wd5.myworkdayjobs.com/Cisco_Careers | every 24h | 0 in the newest 200 (no country facet; partial) | Workday site linked from the Phenom-hosted search page. No country facet exposed: the newest pages are scanned and filtered after fetching (partial), so it syncs daily. |
| Cloudflare | Technology | https://www.cloudflare.com/careers/jobs/ | GREENHOUSE | https://boards.greenhouse.io/cloudflare | every 12h | 0 in Africa (356-role board; list fallback) | Public Greenhouse board API (~350 openings when checked); too large to return with descriptions, so the list is read and descriptions fetched for new in-scope roles. |
| NVIDIA | Technology | https://www.nvidia.com/en-us/about-nvidia/careers/ | WORKDAY | https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite | every 24h | 0 of 40 scanned (no country facet) | Workday site linked from jobs.nvidia.com. No country facet exposed: newest pages scanned and filtered (partial), so it syncs daily. |
| Oracle | Technology | https://careers.oracle.com/en/sites/jobsearch | ORACLE_RECRUITING | https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_45001 | every 12h | 0 in Africa | Oracle's own Recruiting site CX_45001 behind careers.oracle.com. |
| Stripe | Technology | https://stripe.com/jobs/search | GREENHOUSE | https://boards.greenhouse.io/stripe | every 12h | 0 in Africa (632-role board; list fallback) | Public Greenhouse board API (~630 openings when checked); too large to return with descriptions, so the list is read and descriptions fetched for new in-scope roles. |

## Ready — official pages with structured data

| Company | Group | Official careers URL | ATS / route | Fetched endpoint | Sync | Live sync (2026-09-15) | Notes |
|---|---|---|---|---|---|---|---|
| EY | Consulting | https://www.ey.com/en_gl/careers | SUCCESSFACTORS | https://careers.ey.com/ey/ | every 12h | 4 in Nigeria (Lagos) | SAP SuccessFactors career site: search results link each posting, whose page carries schema.org JobPosting microdata. Scoped by the site's location search. |
| Caterpillar | Engineering / Industrial | https://careers.caterpillar.com/en/ | — | https://careers.caterpillar.com/en/ | every 12h | 0 of the first results page (20 roles, none in Africa) | The jobs page links postings whose pages carry schema.org JobPosting JSON-LD (with validThrough); first page only, filtered (partial). |
| Chevron | Oil, Gas & Energy | https://careers.chevron.com/ | RADANCY | https://careers.chevron.com/ | every 12h | 0 of the first results page (15 roles, none in Africa) | Job pages carry schema.org JobPosting JSON-LD. robots.txt disallows location-filtered search URLs, so only the unfiltered first results page is read and filtered (partial). |
| ExxonMobil | Oil, Gas & Energy | https://jobs.exxonmobil.com/ | SUCCESSFACTORS | https://jobs.exxonmobil.com/ | every 12h | 0 of the first results page (10 roles, none in Africa) | SAP SuccessFactors career site. The location search returned non-Nigerian roles when checked, so listings are filtered after fetching; only the first results page is read (partial). RSS is disallowed by robots.txt. |
| SAP | Technology | https://jobs.sap.com/ | SUCCESSFACTORS | https://jobs.sap.com/ | every 12h | 1 in Nigeria (Lagos) | SAP SuccessFactors career site with schema.org JobPosting microdata; scoped by location search. |

## Requires configuration

| Company | Group | Official careers URL | ATS identified | Notes |
|---|---|---|---|---|
| KPMG | Consulting | https://kpmg.com/xx/en/careers.html | — | Global job search routes to member-firm sites; each country needs its own source. |
| Cummins | Engineering / Industrial | https://www.cummins.com/careers | — | Careers page reachable; job search ATS not identifiable from public HTML. |
| Siemens | Engineering / Industrial | https://jobs.siemens.com/en_US/externaljobs | — | Portal-style job site; no job links or structured data in the initial HTML. |
| Coca-Cola | FMCG / Manufacturing | https://careers.coca-colacompany.com/ | — | The job search URL redirected to the careers home page; no job links or ATS in public HTML. |
| Coca-Cola HBC | FMCG / Manufacturing | https://www.coca-colahellenic.com/en/careers | — | Careers page is rendered client-side; ATS not identifiable from public HTML. |
| Mondelez | FMCG / Manufacturing | https://www.mondelezinternational.com/careers/ | PHENOM | Phenom-hosted careers front end; the underlying ATS isn't linked in public HTML. |
| GTCO | Nigeria / Africa | https://www.gtbank.com/careers | — | Careers page is rendered client-side; no job list or ATS found in public HTML. |
| HEINEKEN / Nigerian Breweries | Nigeria / Africa | https://www.nbplc.com/careers/ | SUCCESSFACTORS | Links SAP SuccessFactors job invites (theheinekencompany-rmk.jobs.hr.cloud.sap); no public listing page with job links found. |
| Holcim / Lafarge Africa | Nigeria / Africa | https://www.holcim.com/careers | — | Group careers page reachable; its jobs path returned 404 and no ATS link was found. Lafarge Africa not yet audited. |
| Standard Bank Group (Stanbic IBTC) | Nigeria / Africa | https://www.standardbank.com/sbg/standard-bank-group/careers | — | Group job list page has no job links in public HTML; stanbicibtc.com refused automated access (403) when checked. |
| UBA | Nigeria / Africa | https://www.ubagroup.com/careers/ | — | Careers page is rendered client-side; no job list or ATS found in public HTML. |
| Baker Hughes | Oil, Gas & Energy | https://careers.bakerhughes.com/ | — | Careers site is rendered client-side; ATS not identifiable from public HTML. |
| Eni | Oil, Gas & Energy | https://www.eni.com/en-IT/careers.html | ORACLE_RECRUITING | Postings live on jobs.eni.com (Oracle Recruiting site CX_1004 on a custom domain); the REST resource isn't exposed there, and the underlying pod isn't in the public HTML. |
| Halliburton | Oil, Gas & Energy | https://careers.halliburton.com/ | SUCCESSFACTORS | SuccessFactors-based; the /search listing returned 404 when checked. Job pages need re-auditing. |
| Hitachi Energy | Oil, Gas & Energy | https://www.hitachienergy.com/careers | WORKDAY | The careers page references a hitachi.wd1 Workday tenant, but the site name isn't in the public HTML. |
| SLB | Oil, Gas & Energy | https://careers.slb.com/ | — | Job listing is rendered client-side; no ATS or structured data in public HTML. |
| Shell | Oil, Gas & Energy | https://www.shell.com/careers.html | — | Job search is rendered client-side; the ATS isn't identifiable from public HTML. |
| Siemens Energy | Oil, Gas & Energy | https://jobs.siemens-energy.com/en_US/jobs | — | Portal-style job site; no job links or structured data in the initial HTML. |
| TechnipFMC | Oil, Gas & Energy | https://www.technipfmc.com/en/careers/ | — | Careers page reachable; no job list, ATS link or structured data found in public HTML. |
| Weatherford | Oil, Gas & Energy | https://careers.weatherford.com/ | ORACLE_RECRUITING | Oracle Recruiting pod fa-exmi-saasfaprod1.fa.ocs.oraclecloud.com is referenced, but the site number isn't in the public HTML; set site_number to enable. |
| Wärtsilä | Oil, Gas & Energy | https://www.wartsila.com/careers | SUCCESSFACTORS | Links to a SuccessFactors career2.successfactors.eu portal behind a login flow; no public job list or structured data found. |
| Amazon / AWS | Technology | https://www.amazon.jobs/en/ | — | amazon.jobs exposes a public search.json endpoint (robots.txt allows it) with country filters, but CareerOS has no adapter for this custom API yet. |
| GitHub | Technology | https://www.github.careers/careers-home | ICIMS | Postings are on iCIMS portals (careers-githubinc.icims.com); no iCIMS adapter yet and portal links lead to login. |
| IBM | Technology | https://www.ibm.com/careers | — | Job search is rendered client-side; ATS not identifiable from public HTML. |
| Salesforce | Technology | https://www.salesforce.com/company/careers/ | — | Jobs page has no ATS link or structured data in public HTML. |

## Manual only

| Company | Group | Official careers URL | ATS identified | Notes |
|---|---|---|---|---|
| Access Bank | Nigeria / Africa | https://www.accessbankplc.com/ | — | The careers job-opportunities link returned 404 when checked; track announcements manually. |
| Airtel Africa | Nigeria / Africa | https://www.airtel.africa/opportunities | — | Opportunities page has no job links, ATS or structured data in public HTML; track manually. |
| Dangote Group | Nigeria / Africa | https://www.dangote.com/ | — | dangote.com/careers returned 404 when checked; no official careers listing found. |
| Interswitch | Nigeria / Africa | https://interswitchgroup.com | — | No careers listing or ATS board found (the careers URL redirected to the home page; no Greenhouse board). |
| Apple | Technology | https://www.apple.com/careers/ng/ | — | jobs.apple.com redirected to the Nigeria careers overview page; no job list in public HTML. |
| Google | Technology | https://www.google.com/about/careers/applications/jobs/results | — | Results page has no structured data; job links route through sign-in. No public API. |
| Meta | Technology | https://www.metacareers.com/jobsearch/ | — | Job search is rendered client-side with no public structured endpoint. |

## Blocked (access refused; never worked around)

| Company | Group | Official careers URL | ATS identified | Notes |
|---|---|---|---|---|
| BCG | Consulting | https://careers.bcg.com/ | — | Refused automated access (HTTP 403) when checked. |
| McKinsey | Consulting | https://www.mckinsey.com/careers/search-jobs | — | Job search is disallowed by robots.txt. |
| PwC | Consulting | https://www.pwc.com/gx/en/careers.html | — | Refused automated access (HTTP 403) when checked. |
| Bosch | Engineering / Industrial | https://jobs.bosch.com/en | SMARTRECRUITERS | Postings are on SmartRecruiters (BoschGroup), whose API robots.txt disallows general crawlers. |
| Rolls-Royce | Engineering / Industrial | https://careers.rolls-royce.com/ | — | Refused automated access (HTTP 403) when checked. |
| Tesla | Engineering / Industrial | https://www.tesla.com/careers/search/ | — | Refused automated access (HTTP 403) when checked. |
| Diageo / Guinness Nigeria | FMCG / Manufacturing | https://www.diageo.com/en/careers | — | Refused automated access (HTTP 403) when checked. |
| Mars | FMCG / Manufacturing | https://careers.mars.com/ | — | Refused automated access (HTTP 403) when checked. |
| Nestlé | FMCG / Manufacturing | https://www.nestle.com/jobs | — | Refused automated access (HTTP 403) when checked. |
| Paystack | Nigeria / Africa | https://paystack.com/careers | — | Refused automated access (HTTP 403); no public Greenhouse board found. |
| Seplat Energy | Nigeria / Africa | https://www.seplatenergy.com/careers | — | Refused automated access (HTTP 403) when checked. Not worked around; track manually. |
| Saipem | Oil, Gas & Energy | https://www.saipem.com/en/careers | — | Refused automated access (HTTP 403) when checked. |
| Schneider Electric | Oil, Gas & Energy | https://careers.se.com/ | — | Refused automated access (HTTP 403) when checked. |
| Wood | Oil, Gas & Energy | https://careers.woodplc.com/ | — | Refused automated access (HTTP 403) when checked. |
| bp | Oil, Gas & Energy | https://www.bp.com/en/global/corporate/careers.html | — | Refused automated access (HTTP 403) when checked. |
| Microsoft | Technology | https://careers.microsoft.com/v2/global/en/home.html | EIGHTFOLD | Careers run on Eightfold; its jobs API refused automated access (HTTP 403). |

## Registered outside the starter pack

Sources added earlier through live discovery remain registered and are not part of the pack: Greenhouse boards for Jumia,
One Acre Fund, GiveDirectly, Teach For All, Canonical, Ozow, Luno and Acumen; Ashby boards for M-KOPA and Andela; the
Renaissance Africa Energy Flair board (`listing_complete: true`); newsroom and media RSS feeds; and editor-researched
scholarship providers. See DISCOVERY_ENGINE.md §16.

## Re-auditing

Career sites change platforms. Re-check a source with **Test connection**; when its route changes, update the pack entry
(URL, `ats_provider`, `readiness`, note) and re-import — operational settings admins chose are preserved.
