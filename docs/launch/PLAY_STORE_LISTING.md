# Google Play listing — CareerOS (draft)

Everything below is ready to paste into Play Console. Only claims the app actually delivers are
made: no invented user counts, no "AI-powered", no success-rate promises.

## Store presence

- **App name (30 max):** `CareerOS: Jobs & Career Prep` (28)
- **Short description (80 max):**
  `Real jobs and scholarships, application tracking, and practice that gets you ready.` (79)
- **Category:** Business · **Tags:** Jobs, Career, Education
- **Contact email:** <YOUR CONTACT EMAIL>
- **Privacy policy URL:** the published `docs/launch/PRIVACY_POLICY.md` page
- **Content rating:** Everyone (no user-generated public content, no ads in sensitive flows)
- **Target audience:** 18+ (16+ acceptable; the policy states 16 and over)
- **Ads:** Yes — the app contains ads
- **In-app purchases:** No (CareerOS Pro is not purchasable yet)

## Full description (4000 max)

```
CareerOS brings the whole job hunt into one place: real opportunities, the applications you're
chasing, and the preparation that decides whether you get the offer.

FIND REAL OPPORTUNITIES
• Jobs, internships, graduate programmes and scholarships, collected from employers' own career
  pages and official application portals
• Every listing links to the official application page — you apply where the employer wants you to
• Filter by country, region, work mode, employment type and field
• Listings are re-checked at their source, and ones that close are marked instead of quietly rotting

TRACK EVERY APPLICATION
• One place for every role you've applied to, from saved to offer
• Stage history, interview dates, notes and deadlines
• Nothing changes without you: CareerOS never moves an application stage on its own

PREPARE WITH PURPOSE
• Aptitude practice: numerical, verbal, abstract, logical, situational judgement and technical
• Timed mock assessments, or practice at your own pace with explanations for every answer
• Interview practice: company, technical and behavioural questions, with recording and self-rating
• STAR story builder so your best examples are ready before the interview
• Progress you can see — scores by section, questions practised, stories ready

SHARPEN YOUR CV
• See how your CV reads against common applicant tracking system patterns
• Compare it with a specific job description: matched keywords, gaps, suggested improvements
• Honest about what it is: an estimate against common parsing patterns, not a peek at any
  employer's private screening system

COMPANY INTELLIGENCE
• Follow companies and see hiring news, expansions and programmes before the roles appear

PRIVACY YOU CAN CHECK
• Your CV, recordings and application history are never sent to third-party AI services
• Optional mailbox connection is read-only, never stores email bodies, and can be disconnected at
  any time — the app is fully usable without it
• Ads never appear during tests, interviews, results or account settings

CareerOS is built for people who want a clear, honest view of where their career search stands.
```

## Graphics

| Asset | Spec | Source |
|---|---|---|
| App icon | 512×512 PNG | `mobile/assets/brand/` master (already the launcher icon) |
| Feature graphic | 1024×500 PNG | generate from the brand board (navy gradient + logo + tagline) |
| Phone screenshots | 2–8, min 1080px wide | capture on the emulator from the live build |

Screenshot set (in order, each with a short caption):
1. Home — "Your career at a glance"
2. Opportunities feed — "Real jobs, internships and scholarships"
3. Job detail — "Apply on the employer's own site"
4. Applications — "Track every stage"
5. Prepare hub — "Practice what interviews actually test"
6. Aptitude results — "See where you're strong"
7. CV & Career Tools — "Check your CV against the role"

Use the live build against the production API so screenshots show real listings. Do not use the
UI-audit renders: they contain sample data.

## Data safety form answers

| Question | Answer |
|---|---|
| Does your app collect or share user data? | Yes, collects; no sharing with third parties |
| Data encrypted in transit? | Yes |
| Users can request deletion? | Yes — in-app account deletion |
| Personal info: name, email | Collected · account management · required |
| Personal info: other (professional title, location, education) | Collected · app functionality · optional |
| Files & docs: CV text | Collected · app functionality · optional (original file not retained) |
| Audio: voice recordings | Collected · app functionality · optional (interview practice playback) |
| App activity: in-app actions, search history | Collected · app functionality · required |
| Messages: emails | **Not collected** in this release — mailbox connection ships disabled. If you enable it later, update this form: metadata only (sender, subject, date), bodies never stored |
| Device or other IDs | Collected by the ads SDK · advertising · required when ads are on |

## Release notes (first release)

```
First public release of CareerOS: real opportunities from employers' own career pages, application
tracking with full stage history, aptitude and interview practice with explanations, STAR stories,
and CV analysis against common applicant tracking patterns.
```

## Before you submit

- Sign the AAB with your own upload keystore (`RENDER_LAUNCH.md` step 4) — a debug-signed build is
  rejected.
- The privacy policy URL must be live and reachable from a browser with no login.
- Test the exact AAB you upload via Play Console's internal testing track first; the app must be
  able to reach the production API.
- Mention nothing about Gmail/Outlook tracking in the listing while it ships disabled: Google's
  restricted-scope review applies the moment the app requests those scopes.
