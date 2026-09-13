# Design Tokens

All mobile tokens live in `mobile/lib/core/design/` and are exported by `design.dart`
(`import "package:careeros/core/design/design.dart";` or the relative path). Admin mirrors them in
`admin/tailwind.config.ts` (`careeros.*` colors) and CSS variables in `admin/app/globals.css`.

## Color

### Brand & semantic constants — `AppColors` (same in light and dark)
| Token | Hex | Use |
|---|---|---|
| `navy` | `#071A38` | Brand, hero grounds, wordmark "Career" |
| `blue` | `#1677FF` | Primary actions, links, active nav, "OS" |
| `brightBlue` | `#249BFF` | Blue on dark grounds, gradients |
| `cyan` | `#13BDEB` | Accent, gradient end, "Screening" status, info |
| `success` | `#18B76A` | Success, offers, completed, fully funded |
| `warning` | `#F5A623` | Deadlines approaching, interviews, caution |
| `error` | `#E84D5B` | Errors, destructive actions, rejected, urgent |
| `purple` | `#7557FF` | Assessments, preparation accents |

Do not introduce feature-specific colors. If something needs color, map it to a semantic tone
(`AppTone.primary/info/success/warning/danger/purple/neutral`).

### Mode-dependent surfaces — `context.colors` (`CareerColors` ThemeExtension)
| Token | Light | Dark |
|---|---|---|
| `background` | `#F6F8FC` | `#07111F` |
| `surface` | `#FFFFFF` | `#0C1B31` |
| `surfaceElevated` | `#FFFFFF` | `#112642` |
| `surfaceMuted` (grouping, skeletons, input fill) | `#EEF2F8` | `#0F2139` |
| `textPrimary` | `#10213D` | `#F6F9FF` |
| `textSecondary` | `#66758C` | `#9AA9BD` |
| `border` | `#E6EBF2` | `#1D3352` |
| `primary` (blue tuned per mode) | `#1677FF` | `#249BFF` |
| `heroGradient` | navy → `#0D3B84` → blue | `#0C1B31` → `#112642` → `#0D3B84` |

Dark mode is designed, not inverted: surfaces step up in lightness for elevation (instead of
shadows), text is off-white, primary shifts to `brightBlue` for contrast, tinted backgrounds use
lower alpha. Tone tints: `tone.color.withValues(alpha: isDark ? 0.18 : 0.10)` via `AppTone.tint(context)`.
Text placed on a tint uses `AppTone.onTint(context)` (amber/cyan/green are darkened in light mode so
small labels stay readable). Theme mode is user-selectable (Settings → Appearance) and persisted in
`AppPreferences` via `themeModeProvider`.

## Typography — `AppTypography` → `Theme.of(context).textTheme` (`context.text`)
Family: **Plus Jakarta Sans** preferred (not yet bundled) → Inter → SF Pro / Roboto (platform
default, current). Switch `AppTypography.fontFamily` once the font files are added to pubspec.

| Role | TextTheme slot | Size / weight |
|---|---|---|
| Display | `displaySmall` | 32 / w800, -0.5 tracking |
| Page title | `headlineMedium` | 26 / w700 |
| Section title | `titleLarge` | 19 / w700 |
| Card title | `titleMedium` | 16 / w600 |
| Body | `bodyLarge` | 15 / w400, textPrimary |
| Body (secondary) | `bodyMedium` | 14 / w400, textSecondary |
| Supporting | `bodySmall` | 12.5 / w400, textSecondary |
| Button / label | `labelLarge` | 15 / w600 |
| Micro / chip | `labelSmall` | 11 / w600, +0.2 tracking |

Never hardcode `fontSize` in features; use a slot and `copyWith(color:)` if needed.

## Spacing — `AppSpacing` (8-pt scale)
`xxs 4 · xs 8 · sm 12 · md 16 · lg 20 · xl 24 · xxl 32 · xxxl 40 · huge 48`
- Page horizontal padding: `AppSpacing.pageH` = 20 (`AppSpacing.page` insets). Dense pages: 16.
- Gap between major sections: 28 (`AppSpacing.section`).
- Card inner padding: 16 (standard) / 20 (feature, hero).

## Radius — `AppRadius`
`sm 8` small controls · `md 12` inputs/buttons (`button` 14) · `card 16` · `feature 20` · `hero 24`
· `sheet 24` (top corners) · `pill 999` (chips, filters, tags, statuses only).

## Elevation — `AppShadows`
Light: 1 px `border` + soft shadow (`AppShadows.card`: navy @ 4%, blur 16, y 4; `raised`: 8%, blur
24, y 10). Dark: no shadows — use `surfaceElevated` + border. Never use Material elevation > 1.

## Motion — `AppMotion`
`fast 180ms` (press, chip toggle) · `normal 240ms` (state changes, progress) · `slow 280ms` (sheets,
route-level) · curve `Curves.easeOutCubic`. No bounce, glow or looping decorative animation.
Respect `MediaQuery.disableAnimations`.

## Icons — `AppIcons`
Material Symbols *rounded/outlined* family only. Use semantic names (`AppIcons.opportunities`,
`AppIcons.prepare`, `AppIcons.cv`, `AppIcons.deadline`, …) so a concept always has the same glyph.
Filled variant only for the selected bottom-nav destination.
