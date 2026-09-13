# CareerOS Brand System

## Positioning
CareerOS is about **career progression**, not graduation. The identity communicates direction,
growth and arrival: *C = Career · Path = Career journey · Arrow = Progress · Upward movement =
Growth · Spark = Achievement / destination.*

## The mark (pathway C)
- Source of truth: `assets/brand-reference/careeros-mark.svg` (64×64 viewBox).
- Flutter: `CareerOSMark(size:, onDark:)` in `mobile/lib/core/widgets/careeros_logo.dart` — a
  `CustomPainter` that replays the same SVG geometry, so the widget and the SVG never drift.
- Anatomy: navy C stroke (opening to the upper-right) · blue→cyan gradient pathway that starts
  inside the C and exits through the opening · arrowhead · small cyan four-point spark.
- On navy/dark grounds use the reversed variant (`onDark: true` / `careeros-mark-on-dark.svg`):
  the C becomes white, pathway and spark keep their blue/cyan.
- Minimum size: 20 px (favicon). Below 24 px drop the wordmark and use the mark alone.
- Clear space: at least 25% of the mark's width on every side.
- Don't: recolor the C in feature colors, add drop shadows/glows, rotate, outline, place on busy
  imagery, stretch, or rebuild it from icon-font glyphs.

## Wordmark
`CareerOS` — "Career" in Deep Navy `#071A38`, "OS" in Electric Blue `#1677FF`. Bold/ExtraBold,
slight negative tracking (-0.5 at 28 px). On dark grounds "Career" becomes `#F6F9FF`; "OS" stays
blue (`#249BFF` for contrast). Flutter: `CareerOSWordmark`, lockup `CareerOSLogo`.

## App icon
Master: `assets/brand-reference/careeros-app-icon.svg` — navy gradient ground, reversed mark inside
the 66% adaptive-icon safe zone. Android uses an adaptive icon (vector foreground + navy
background) with PNG mipmaps for API 24–25; iOS uses the flattened PNG set. The Android 12+ system
splash reuses the icon on navy.

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
