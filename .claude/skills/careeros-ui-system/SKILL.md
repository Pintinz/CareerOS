---
name: careeros-ui-system
description: Authoritative CareerOS UI/UX design system for the Flutter mobile app and the Next.js admin portal. Use whenever creating or redesigning a CareerOS screen, building shared Flutter widgets, changing navigation, working on dark mode, touching the admin portal's look, or doing an accessibility / UI-consistency review.
---

# CareerOS UI System

> Every CareerOS screen must look and behave like it belongs to the same product.

CareerOS should feel **premium, calm, trustworthy, intelligent and ambitious** — never like a
generic Flutter template, a school portal, a job board clone, a crypto dashboard, an AI demo, or
an ad-driven app.

## Non-negotiables

1. **Truthful UI.** Never render a number, score, match, eligibility %, readiness value, company
   metric, salary, verification badge or notification that the backend did not produce. If the
   data does not exist, omit the element or show an honest fallback. Mockups are direction, not data.
2. **Tokens, not literals.** Colors, text styles, spacing, radii, shadows and motion come from
   `mobile/lib/core/design/` (admin: `admin/tailwind.config.ts` + `admin/app/globals.css`).
   No raw hex, no ad-hoc `EdgeInsets`, no one-off radii in feature code.
3. **Shared components first.** Reuse `mobile/lib/core/widgets/` before building a new card,
   button, chip, empty/error/loading state, sheet or dialog. Never create a second version of an
   existing pattern — extend the shared one.
4. **One primary CTA per screen.** Everything else is secondary (tonal/outline) or tertiary (text).
5. **Brand = the official logo** (`assets/brand-reference/careeros-brand-board.png`: navy C, rising
   ribbon arrow, spark). Use `CareerOSMark` / `CareerOSWordmark` / `CareerOSLogo` (Flutter) or
   `BrandMark` / `BrandLockup` (admin) — never redraw it or set the wordmark as live text. The
   graduation-cap / award-ribbon identity is retired.
6. **Theme-aware.** Mode-dependent colors come from `context.colors` (the `CareerColors` theme
   extension) so light and dark both work. `AppColors.*` is only for brand/semantic constants.
7. **Ads are always labelled "Advertisement"**, visually distinct from content, and never appear
   in forbidden contexts (active tests, mock interviews, results, auth, onboarding, settings).
8. **No functionality loss.** Redesigns keep every route, provider, callback and test-visible
   behaviour. Update widget-test assertions intentionally; never delete a test to pass.

## Workflow for any screen

Before editing, note (briefly, in your head or the PR): current screen → UX problem → system
solution → components reused → functional risk. Then:

1. Identify the screen's hub (Home / Opportunities / Prepare / Intelligence / Profile) and its
   single primary action.
2. Build with shared components and tokens; group with spacing + `SectionHeader` before adding
   containers (avoid card-in-card).
3. Handle **loading** (skeletons for feeds/lists, spinners only for buttons/blocking actions),
   **empty** (title + helpful sentence + next action) and **error** (friendly copy + Retry; never a
   raw exception) states.
4. Check small phones (360 logical px), large text (1.3× scale), and dark mode.
5. Run `flutter analyze` and the relevant widget tests. Add new top-level screens to
   `mobile/test/ui_audit/ui_audit_test.dart` — it renders each screen in light + dark at 360dp and at
   320dp with 1.3× text and fails on any overflow. For visual QA without a backend:
   `flutter test test/ui_audit --dart-define=UI_AUDIT_CAPTURE=true` → `mobile/build/ui_audit/*.png`
   (add `--dart-define=UI_AUDIT_HEIGHT=1500` to capture whole scrolling pages and
   `--dart-define=UI_AUDIT_ONLY=<name part>` to run a subset). Images decode asynchronously, so a
   brand logo can be missing from the first capture of a run — check the next screen before calling it a bug.

Screen quality questions are in `references/ux-rules.md` and visual polish rules in
`references/visual-quality.md` — go through both before calling a screen done.

## Reference map

| Need | Read |
|---|---|
| Logo, wordmark, taglines, voice, retired assets | `references/brand-system.md` |
| Color / type / spacing / radius / shadow / motion tokens + code names | `references/design-tokens.md` |
| Bottom navigation, hubs, information architecture, routing rules | `references/mobile-navigation.md` |
| Per-screen layouts (Home, feeds, details, tracker, Prepare, tests, ATS, Profile, Settings) and shared component catalogue | `references/screen-patterns.md` |
| Touch targets, semantics, contrast, text scaling, color-independence | `references/accessibility.md` |
| Admin portal shell, tables, forms, badges, brand | `references/admin-design.md` |
| Truthfulness, CTA hierarchy, empty/error/loading copy, progressive disclosure, ads, QA checklist | `references/ux-rules.md` |
| Text hierarchy, copy casing, card family, metrics, progress, chips, empty/error visuals, admin stats | `references/visual-quality.md` |

Brand files: `assets/brand-reference/` (brand board + generated symbol/wordmark/app-icon masters). Visual north star:
`assets/ui-reference/careeros-mockup-board.png` — read `assets/ui-reference/README.md` first for what
to take from it and what is fictional. Screenshot QA captures also belong in `assets/ui-reference/`.
