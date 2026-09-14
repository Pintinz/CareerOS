# UI reference

## `careeros-mockup-board.png` — visual north star
The supplied 21-screen board (splash → settings, plus admin). Treat it as **direction, not data**.

Take from it:
- Light, airy surfaces: white cards on `#F6F8FC`, soft borders, generous spacing.
- **Pill tabs / segmented filters**: selected = filled electric blue with white text, others =
  secondary text on a muted pill track (`CareerPillTabBar`, selected `AppFilterChip`).
- Home: plain greeting row + avatar, a white progress/score card with a ring, a 2×2 stat grid,
  then a short "for you" list — not an endless feed.
- Detail screens: banner image hero, logo overlapping the banner edge, title + tag chips,
  underline tabs (Overview / Requirements / Company), bottom Save (outline) + Apply (filled), a
  tonal full-width secondary action below.
- Tools lists (CV & Career Tools, Settings): tinted icon tile · title · one-line description · chevron.
- Profile: navy hero with photo, name, title, location; tabs below.
- Tracker rows: logo · role · company · stage/date · status pill.
- Admin: navy sidebar with blue active item, stat tiles, tables with Live/Draft pills and Edit actions.

Do **not** take from it (not real in CareerOS today, or forbidden by ux-rules.md):
- Any number: Career Score 82/100, 92% match, 84% eligibility, 72% interview readiness, skill bars,
  admin counts, "Trusted by…" claims.
- Continue with Google / Apple sign-in (not implemented).
- A bottom-nav "AI" tab or "Career AI" branding — the hub is **Prepare**, the tool list is
  **CV & Career Tools**.
- Tools that don't exist yet (cover letter generator, bullet improver, offer comparison, roadmap)
  as active entries.
- The mockup's splash glyph — the official logo is in `../brand-reference/careeros-brand-board.png`.

## Screenshot QA
Put emulator/device capture sets here as `qa-YYYY-MM-DD/<screen>.png` with a contact sheet.
