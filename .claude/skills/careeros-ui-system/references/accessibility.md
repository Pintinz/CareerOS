# Accessibility

Target: WCAG 2.2 AA equivalents on mobile and admin.

## Touch & layout
- Minimum interactive size 48×48 dp (44 pt iOS). Icon buttons use `IconButton` (48 dp default) —
  never shrink with `VisualDensity.compact` unless the row itself is ≥ 48 dp tall and tappable.
- Keep 8 dp between adjacent targets.
- Layouts must survive 360 dp width and 1.3× text scale without overflow: use `Expanded`,
  `Flexible`, `Wrap`, `maxLines` + `TextOverflow.ellipsis` on single-line titles, and never fix a
  container height that holds text (use `constraints: BoxConstraints(minHeight: …)`).

## Semantics
- Every `IconButton` has a `tooltip` (doubles as the screen-reader label).
- Decorative images/icons: `excludeFromSemantics: true` or `ExcludeSemantics`.
- Custom tappable containers (`InkWell` cards) wrap content in `Semantics(button: true, label: …)`
  when the visible text alone is ambiguous.
- Progress rings/bars expose `Semantics(label: "Career setup", value: "3 of 5 complete")`.
- Timers announce politely; don't re-announce every second.
- Recording state is announced ("Recording started" / "Recording stopped").

## Color & contrast
- Body text ≥ 4.5:1, large text/icons ≥ 3:1 against their surface in both modes. `textSecondary`
  on `surface` passes in both palettes; don't lighten it further.
- Never communicate state with color alone: status chips carry text (and icon where useful),
  correct/incorrect answers use ✓/✕ icons plus text, required fields have text errors.
- Tinted backgrounds (10–18% alpha) hold text in the full-strength tone color *only* for labels
  ≥ 11 px semibold; body copy stays `textPrimary`.

## Text scaling
Respect system font size. Don't clamp `textScaler` globally. Test key screens at 1.3×.

## Motion
Honor `MediaQuery.disableAnimationsOf(context)` — skip decorative transitions and progress tweens.

## Forms
Labels always visible (floating label or above-field label), errors in text below the field,
keyboard type and `textInputAction` set, autofill hints for email/password.

## Admin
Semantic HTML (`nav`, `main`, `table`, `th scope`), visible focus rings (`focus-visible:ring-2
ring-careeros-blue`), buttons are `<button>`, icon-only buttons have `aria-label`, status badges
include text.
