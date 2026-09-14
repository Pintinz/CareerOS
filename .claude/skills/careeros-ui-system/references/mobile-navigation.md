# Mobile Navigation & Information Architecture

## Five hubs (bottom navigation — fixed order)
| Tab | Question it answers | Contains |
|---|---|---|
| **Home** | What matters to me today? | Greeting, setup/progress, recruitment activity, next action, quick actions, latest opportunities, upcoming stages, scholarships, intelligence |
| **Opportunities** | What can I pursue? | Jobs · Internships · Entry Level · Scholarships tabs, search, filters, saved items |
| **Prepare** | How do I become more competitive? | Aptitude tests, interview preparation, STAR stories, CV & Career Tools (ATS), history, analytics, resume-active-session |
| **Intelligence** | What should I know about companies & careers? | Company intelligence feed, categories, following filter, company profiles |
| **Profile** | Who am I professionally? | Career passport, CV, applications tracker entry, saved, settings |

Rules:
- No other permanent tabs. Jobs, Scholarships, ATS and Tests live *inside* hubs.
- Implemented as `HomeShell` (`IndexedStack` + `NavigationBar`); tabs keep scroll/state.
  In-shell jumps use `HomeShell`'s `onSelectTab` callback, not `context.go("/home")`.
- "Graduate programmes" have no distinct data type yet; the **Entry Level** tab filters
  `experience_level=ENTRY` and must not be labelled as graduate programmes until a real type exists.

## Routing (GoRouter — `mobile/lib/routing/app_router.dart`)
- Keep every existing path; redesigns must not rename routes (deep links, tests, notifications).
- Detail and task screens are pushed (`context.push`) on top of the shell so back returns to the hub.
- Distraction-free flows (active aptitude test, mock interview session) are full-screen pushed
  routes with no bottom nav and no ads; exits confirm when progress would be lost.
- Auth/onboarding/splash are outside the shell; redirects in `routerProvider` stay authoritative.
- Signed-out flow: `/splash` → `/welcome` (front door) → **Get Started** → `/onboarding` carousel →
  `/register`; **Log in** → `/login`. Every signed-out redirect lands on `/welcome`. Signed-in users
  are kept out of these routes, except `/onboarding?replay=1` (Settings → App introduction), which
  pops back when done.

## Screen chrome
- Hub roots: large page title inside the scroll view (no AppBar), optional trailing actions
  (search/settings) as 48 px icon buttons with tooltips.
- Pushed screens: `AppBar` with back button, title in `titleLarge`, max two trailing actions; extra
  actions go in an overflow menu or a bottom sheet.
- Tabs inside a screen: `TabBar` with blue indicator, label `labelLarge`, left-aligned & scrollable
  when more than 3 tabs.
- Primary CTA on detail screens: pinned bottom action bar (`BottomActionBar`) with safe-area
  padding; secondary action beside it as an outline/tonal button.

## Progressive disclosure
Use tabs, expandable sections, bottom sheets (filters, stage updates, question navigator) and
detail routes instead of stacking every capability on one scroll.
