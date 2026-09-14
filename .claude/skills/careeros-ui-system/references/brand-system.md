# CareerOS Brand System

## Positioning
CareerOS is about **career progression**, not graduation. The identity communicates direction,
growth and arrival: *C = Career · Ribbon = Career journey · Arrow = Progress · Upward movement =
Growth · Spark = Achievement / a brighter tomorrow.*

## The logo (owner-supplied)
Source of truth: `assets/brand-reference/careeros-brand-board.png` — the official brand board
(primary logo + tagline, symbol, app icon). It exists only as a 1448×1086 raster; every other brand
file is cut from it by `mobile/tool/generate_brand_assets.py`. Never redraw, trace or "improve" the
logo by hand — if a vector or larger export becomes available, drop it in and re-run the script.

- **Symbol:** a bold navy C (gradient toward blue at its upper tip) · a blue→cyan ribbon that sweeps
  from inside the C, around its lower curve and up through the opening into an arrowhead · a
  four-point blue spark top-right.
- **Masters** (`assets/brand-reference/`): `careeros-symbol.png`, `careeros-symbol-on-dark.png`,
  `careeros-wordmark.png`, `careeros-wordmark-on-dark.png` (transparent, native resolution) and
  `careeros-app-icon.png` (1024, generated composition matching the board's icon).
- **On dark grounds** use the on-dark variants, as on the board's app icon: the C and "Career"
  become white; ribbon, arrow, spark and "OS" keep their blues.
- Flutter: `CareerOSMark(size:, onDark:, decorative:)`, `CareerOSWordmark(height:, onDark:)`,
  `CareerOSLogo(markSize:, onDark:)` in `mobile/lib/core/widgets/careeros_logo.dart`
  (assets in `mobile/assets/brand/` at 1x/2x/3x). `onDark` defaults to the theme brightness. Pass
  `decorative: true` when a wordmark or title beside it already says "CareerOS".
- Admin: `BrandMark` / `BrandLockup` in `admin/components/BrandMark.tsx` (files in
  `admin/public/brand/`).
- **Primary lockup proportions** (from the board): wordmark height = 0.41 × symbol height, top of
  the wordmark at 0.37 × symbol height, starting just under the spark's tip. **Stacked** (splash):
  symbol above the wordmark, wordmark ≈ 1.5 × the symbol's width, tagline below.
- Minimum size: symbol 20 px; below 24 px use the app icon tile instead of the bare symbol.
- Clear space: at least 25% of the symbol's width on every side.
- Don't: recolor the logo in feature colors, add shadows/glows/outlines, rotate, stretch, place the
  full-colour symbol on dark/busy grounds, or set "CareerOS" in a UI font as a stand-in for the
  wordmark.

## Wordmark
`CareerOS` in the board's geometric bold typeface — "Career" deep navy, "OS" electric blue (matches
`AppColors.navy` / `AppColors.blue`). Always use the wordmark image, never live text. Accessible
name "CareerOS".

## App icon
Deep-navy tile with a blue glow from the top-right and the on-dark symbol at ~72% of the tile width,
as on the board. Generated per platform: Android adaptive icon (`mipmap-*/ic_launcher_background`,
`_foreground` with the symbol inside the 66 dp safe circle, `_monochrome` for themed icons) plus
legacy/round PNGs; iOS AppIcon set; admin `app/icon.png` + `app/apple-icon.png`. Launch screens
(Android 7–11 `splash_logo`, iOS `LaunchImage`) show the on-dark symbol on navy; the Android 12+
system splash reuses the adaptive icon. The 1024 px icons are upscaled ~1.3× from the board, so
they are slightly soft — a larger/vector logo export would fix that.

## Retired identity (do not reintroduce)
- Graduation cap / mortarboard (`Icons.school` as a *brand* symbol).
- Award ribbon / `Icons.workspace_premium` as the splash or logo symbol.
- Flutter default launcher icon or default splash logo.
`Icons.school_outlined` may still be used as a *content* icon for scholarships/education data —
never as the CareerOS logo.

## Taglines & voice
- Primary tagline: **Opportunities Today. A Brighter You Tomorrow.** — splash, onboarding finale,
  store listing, website. Not on everyday product screens.
- Supporting phrase: **Plan. Prepare. Apply. Grow.** — marketing, empty onboarding moments.
- Product voice: clear, encouraging, specific, never hype. Prefer "Analyze CV" over "AI Resume
  Magic"; "Interview Preparation Readiness" over "Chance of passing". Sentence case for body and
  buttons; Title Case only for screen titles and tabs.
- Avoid "AI" branding unless a feature genuinely uses a model — deterministic scoring is described
  as scoring/checks, never "AI scoring".
