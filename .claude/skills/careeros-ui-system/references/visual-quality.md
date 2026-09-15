# Visual Quality: Text, Cards, Stats & Content Presentation

CareerOS must look elegant, premium and deliberately designed — never plain, crowded, boxy or
mechanically generated. Beauty never overrides truth (see ux-rules.md → Truthful UX).

## Typography
- One clear hierarchy per screen: page title (`headlineMedium`) → section title (`titleLarge`, 18/w700)
  → card title (`titleMedium`/`titleSmall`) → body (`bodyLarge`/`bodyMedium`) → supporting (`bodySmall`,
  `labelMedium` 13/w500) → micro (`labelSmall`, chips only).
- Bold is for titles and values. Supporting labels are medium weight; never stack three bold lines.
- No hardcoded font sizes, no more than ~4 sizes visible at once, generous line height, short copy.
- No all-caps labels except one small eyebrow per admin page/panel. List-group labels are sentence case.
- Numbers use tabular figures (`FontFeature.tabularFigures()` / `tabular-nums`).

## Copy casing
- Section headers (`SectionHeader`, `DetailSection`): Title Case — "Latest Opportunities", "Key Details",
  "About the Role". Question-style headers keep sentence punctuation ("What are you preparing for?").
- List-group labels (`CareerListGroup`), chip text, body copy: sentence case.
- Navigation link on sections: "View all" + chevron. In-place actions ("Edit") pass
  `actionNavigates: false` (no chevron).
- Editorial, human wording: "Recent Applications", "Where your tracked roles stand" — never robotic
  feature names or technical labels.

## Section headers
Title + optional one-line description (`subtitle`, `bodySmall`) + optional "View all". Descriptions say
what the section contains and must be true ("The newest roles published on CareerOS"). Keep them to one
line on a 360dp phone.

## Card family (one visual DNA)
All cards share: 16px radius (20 for feature), hairline `border` + `AppShadows.card` in light / surface
step + border in dark, 16px padding (20 feature), title → metadata → chips → action order.
- `CareerCard` variants: standard · feature · muted · outlined.
- `InsightCard`: same surface as CareerCard; tone lives in the circular icon and the "Action →" link.
  No colored edge rails.
- Content order — Job: logo · title · company (+verified) · location • work mode · tags + posted time ·
  save. Intelligence: company · category · headline · summary · time. Application: role · company ·
  stage chip · applied date · chevron.
- No text hugging edges, no floating unaligned icons, no oversized buttons inside small cards, no
  card-in-card.

## Metrics
- `StatCard`: large value (headlineSmall, tabular) with a 32px tinted icon top-right → label
  (`labelMedium`) → optional `caption` (short, truthful descriptor: "of 3 written", "Not enough data yet")
  → optional `progress` bar only when the value is a share of a real maximum (a % score, x of y).
- Captions must fit one line at 360dp (≈ 20 characters).
- Hero metrics sit in one translucent strip inside the hero, divided by hairlines, each tappable.
- Never a delta, trend, "match" or readiness value the backend didn't compute. Missing → "—" plus an
  honest caption.

## Progress
`CareerProgressBar` and `CareerProgressRing` draw a same-hue gradient (lighter → tone) on a tinted track,
rounded caps, animated with `AppMotion`. No stock Material indicators for data progress (spinners only
for loading).

## Chips & badges
Compact, readable, semantic tone, always text (icon optional): `StatusChip` (pill) for states,
`TagChip` (8px radius) for facts. Never oversized or decorative.

## Empty & error states
Concentric soft halo around the icon (primary for empty, warning for errors) → title → one helpful
sentence → one action. Error default title: "We couldn't load this section"; message tells the user what
to do ("Please check your connection and try again.") + Retry. Never raw exception text.

## Density & balance
Information-rich, not crowded: group with section headers and whitespace before adding containers, vary
visual weight (one hero, then calm cards), avoid walls of equal cards and stacked dividers.

## Light & dark
Light: soft `background`, white surfaces, restrained shadows, tasteful accents. Dark: deep navy surfaces
that step up in lightness for elevation, off-white text, lower-alpha tints, no glow or neon.

## Admin
- `OverviewCard`: label top-left, icon top-right, large tabular value, optional truthful `hint`
  ("Needs attention" / "All clear" derived from the value). Long text values step down in size.
- `SectionTitle`: calm title + one-line description instead of uppercase section labels.
- Tables: sentence-case headers, generous rows, subtle hover.

## Before finishing a screen
Does the text hierarchy feel premium? Are the cards balanced and from one family? Do the metrics look
elegant and are they all real? Is it easy to scan, with refined spacing, in light and dark? Does it look
like one world-class product? If not, refine it — then re-run the UI audit captures.
