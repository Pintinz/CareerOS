# Screen Patterns & Component Catalogue

## Shared component catalogue (`mobile/lib/core/widgets/`)
| Component | File | Notes |
|---|---|---|
| `CareerOSMark`, `CareerOSWordmark`, `CareerOSLogo` | `careeros_logo.dart` | Only brand rendering |
| `PrimaryButton`, `SecondaryButton`, `AppOutlineButton`, `DangerButton`, `AppTextButton` | `app_buttons.dart` | `isLoading`, `icon`, `expand` |
| `CareerCard` | `career_card.dart` | Surface + border + radius; `variant: standard/feature/muted/outlined`, optional `onTap` |
| `SectionHeader` | `section_header.dart` | Title, optional subtitle and "See all"-style action |
| `StatCard`, `MetricTile` | `stat_card.dart` | Real values only; `null` renders "—" |
| `InsightCard` | `insight_card.dart` | Tone accent bar + icon + title + body + action (alerts, next action) |
| `StatusChip`, `AppFilterChip`, `TagChip` | `chips.dart` | Status always has text (+icon), never color alone |
| `AppSearchField` | `app_search_field.dart` | Debounce in the caller |
| `EmptyState`, `ErrorState`, `LoadingSkeleton`, `SkeletonList` | `state_views.dart` | See ux-rules copy |
| `CareerProgressBar`, `CareerProgressRing` | `career_progress.dart` | Value 0–1 with semantic label |
| `showCareerBottomSheet`, `showCareerDialog` | `career_sheet.dart` | Handle, 24 px top radius |
| `NetworkImageWithFallback` | `network_image.dart` | Initials/icon fallback, cached |
| `BottomActionBar` | `bottom_action_bar.dart` | Pinned primary + secondary CTA |
| `AppTone` | `../design/app_tone.dart` | Semantic color resolution |

Domain cards live with their feature but are composed from these primitives, one implementation
each: `JobCardTile` (jobs), `ScholarshipCardTile` (scholarships), `IntelligenceCardTile`
(intelligence), `ApplicationCardTile` (applications), `CompanyHeader` (companies).

## Home
Order: greeting hero (date, name, real stats) → recruitment attention cards (only when present) →
quick actions (max 4: Find Opportunities, Analyze CV, Prepare, Track Application) → career setup
progress (checklist from real account state; hides when complete) → latest jobs carousel →
scholarships closing soon → company intelligence (3) → nothing else. No endless feed; every
section has "See all" into its hub. Readiness scores appear only when the backend computes one.

## Feeds (jobs / scholarships / intelligence)
Search field at top → horizontally scrolling filter chips → list. Card hierarchy for jobs:
logo · title · company · location • work mode · employment type · (real match) · posted time ·
bookmark · verified (real) · DEMO chip for demo data. No descriptions on feed cards. Pull to
refresh, skeleton on first load, infinite scroll with a small spinner footer. Ads are separate
`Advertisement`-labelled slots between items, never styled as cards of content.

## Detail screens (job / scholarship / company / intelligence)
Hero (banner or tinted band, logo, title, org, key facts as `TagChip`s) → `TabBar`
(Job: Overview · Requirements · Company; Scholarship: Overview · Eligibility · Documents; Company:
Overview · Jobs · Intelligence) → pinned `BottomActionBar` (Apply / Apply Now primary, Save
secondary). Tertiary actions (Analyze & Tailor CV, Track Application) sit in the Overview tab as
outline buttons or list rows — never equal weight with Apply.

## Application tracker (career CRM)
List: `ApplicationCardTile` — logo, role, company, `StatusChip` for stage, applied date.
Stage tones: Saved neutral · Applied primary · Screening/Received/Review info (cyan) · Aptitude/
Assessment purple · Interview/Final/Assessment centre warning · Offer/Hired success · Rejected/
Withdrawn/Expired danger or neutral. Detail: header + tabs Details · Timeline · Notes · Emails;
timeline uses check (done) / filled dot (current) / hollow (future) markers joined by a rail.
Primary CTA: Update Stage. Historical stage events are never edited or reordered by the UI.

## Prepare hub
Hero "Prepare with confidence" + resume-active-session banner (when a session is in progress) →
three primary area cards (Aptitude Testing, Interview Preparation, CV & Career Tools) → secondary
list rows (History, Analytics, STAR Stories).

## Distraction-free flows
Active aptitude test and mock interview: minimal AppBar (section, "Question X of Y", timer), thin
progress bar, content, bottom Previous/Next bar; flag + navigator sheet. No ads, no bottom nav.
Recording state is unmistakable (red dot + "Recording" text + elapsed time).

## Results
Score hero (`CareerProgressRing` + label) → Correct/Incorrect/Unanswered `MetricTile`s → section
performance bars → strong/weak areas → actions (Review Answers primary, Practice Weak Areas secondary).

## ATS / CV & Career Tools
Title "CV & Career Tools". Show only implemented tools. Results: ATS Readiness + Job Match (when a
job was supplied) → breakdown bars → strengths, missing keywords (chips), recommended improvements.
Copy must say scores estimate readiness against common ATS parsing patterns — never claim to know
an employer's proprietary ATS.

## Profile (career passport)
Hero: avatar/initials, name, professional title, location (real fields only) → quick stats that
exist (CVs uploaded, STAR stories, applications) → sections for real profile data (experience
years, education, field of study) with edit affordance → rows: My Applications, Saved, CV & Career
Tools, Settings. Never show skill percentages that were not measured.

## Settings
Grouped lists with small uppercase group labels: Account · Appearance · Notifications · Smart
Application Tracking · Privacy & Ads · CareerOS Pro · Help & About. Logout and Delete Account
are separated at the bottom; destructive rows use `error` color and a confirmation dialog.
