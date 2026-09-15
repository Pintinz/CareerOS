# Admin Portal Design (Next.js)

The admin is an **operational tool** that shares CareerOS identity. Desktop information density —
do not copy mobile cards onto desktop.

## Shell
- Left sidebar, deep navy `#071A38`, 256 px, fixed. Top: `BrandLockup` (on-dark logo + "Admin")
  (white "Career", blue "OS", muted "Admin").
- Nav items: white/80% text, 20 px outline icons, 40 px rows, 8 px radius. Active item: electric
  blue `#1677FF` background (or 12% blue tint + blue left rail) with white text.
- Order: Dashboard · Jobs · Scholarships · Companies · Intelligence · Question Banks · Media ·
  Sources · Discovery · Users · Notifications · Operations · Audit Logs · Settings.
- Main area: `#F6F8FC` background, page header (title 24 px bold, subtitle, primary action button
  on the right), content max-width none, 32 px padding.
- Favicon: `admin/app/icon.png` + `apple-icon.png` (app icon tile, generated).

## Tokens
Tailwind `careeros` palette in `tailwind.config.ts`: `navy, blue, brightBlue, cyan, bg, surface,
text, muted, border, success, warning, error, purple`. Font stack: `"Plus Jakarta Sans", Inter,
ui-sans-serif, system-ui` (no runtime Google Fonts fetch).

## Patterns
- **Tables**: white surface, 1 px border, 12 px radius container; header row `text-xs uppercase
  tracking-wide text-muted bg-bg`; 44–48 px rows; zebra off; row hover `bg-bg`; numeric columns
  right-aligned; actions right-aligned as text/icon buttons.
- **Filters**: toolbar above tables — search input + select filters + reset link.
- **Forms**: two-column grid on ≥ 1024 px, labels above inputs, helper/error text below, sticky
  footer with Cancel (outline) + Save (primary).
- **Status badges**: pill, 12 px semibold text on 10% tint of the semantic color; always text.
  Draft neutral · Published success · Scheduled info · Archived neutral · Failing error · Verified success.
- **Analytics cards**: `OverviewCard` — label + icon on top, large tabular value, optional truthful
  `hint` derived from the value ("Needs attention" / "All clear"), in a 4–5 column grid. Group them under
  `SectionTitle` (title + one-line description), not uppercase labels. Tables use sentence-case headers.
  See `visual-quality.md`.
- **Side panels / modals** for quick edits and confirmations; destructive confirms in error color.
- **Empty/error states** follow the same copy rules as mobile (`ux-rules.md`).

## Buttons
Primary: blue fill, white text, 8 px radius, 36–40 px height. Secondary: white with border.
Danger: error fill. Ghost: text-only for table row actions. One primary action per page header.
