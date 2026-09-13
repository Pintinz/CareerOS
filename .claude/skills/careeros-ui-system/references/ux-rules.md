# UX Rules

## Truthful UX
Never fabricate: job matches, eligibility %, interview readiness, company metrics, views,
applicant counts, salaries, verification, notifications, streaks, ratings, "trending" labels.
- Value unavailable → omit the element, or show "—" inside an otherwise-real stat group.
- Scores that need minimum data (readiness, weak topics) show an honest "Not enough data yet"
  state with what's needed.
- Demo content always shows a visible `DEMO` chip.
- Mockup numbers are never copied into code.

## CTA hierarchy
One dominant action per screen (filled `PrimaryButton`). Examples: Job detail → Apply ·
Scholarship → Apply Now · Aptitude setup → Start Assessment · Interview → Start Practice · ATS →
Analyze CV · Application → Update Stage. Secondary = tonal/outline; tertiary = text buttons or
list rows. Never place four equal buttons in a row.

## Reduce card overuse
Group with spacing, `SectionHeader` and typography first. No card inside a card inside a card.
A list of homogeneous rows lives in **one** `CareerCard` separated by dividers, or directly on the
background — not one card per trivial row.

## Empty states (always: icon · title · one helpful sentence · next action)
- Applications: "No applications yet" / "Track a job you've applied for and CareerOS will help you
  follow every stage." / [Find Opportunities]
- Saved: "Nothing saved yet" / "Bookmark jobs and scholarships to compare them later." / [Browse Opportunities]
- Feed after filters: "No matches for these filters" / "Try removing a filter or searching a broader term." / [Clear Filters]
- History: "No practice sessions yet" / "Your completed tests and interviews will appear here." / [Start Practicing]
Never "No data found."

## Error states
Friendly, specific, recoverable: "We couldn't load your opportunities." / "Check your connection
and try again." / [Retry]. Map exceptions through `friendlyErrorMessage()`; never render raw
`DioException`/stack text. Inline form errors sit under the field.

## Loading
Skeletons (`SkeletonList`, `LoadingSkeleton`) for feeds, dashboards, cards, lists. Spinners only
inside buttons, small modal operations and blocking submissions. Keep previous content visible
while refreshing.

## Progressive disclosure
Tabs, expandable sections, bottom sheets and detail routes. Advanced filters go in a sheet behind a
"Filters" chip showing the active count.

## Monetization UX
- Ad containers are titled "Advertisement" in `labelSmall` + `textSecondary`, sit on
  `surfaceMuted`, and are separated from content by spacing — never card-styled like a job,
  scholarship, intelligence post or recommendation.
- Forbidden contexts (never ads): splash, onboarding, auth, active tests, mock interviews, results
  review, application detail/stage updates, email tracking review, settings, account deletion.
- Rewarded unlocks explain exactly what is unlocked before showing the ad.

## Email tracking UX
Recruitment intelligence, not an inbox: Detected event · Matched application · Suggested stage ·
Confidence · Reason. Actions: Confirm (primary) · Wrong application · Ignore. Never auto-update a
stage; never show full email bodies.

## Screen quality checklist (run before marking a screen done)
1. What is this screen for, and what does the user need most?
2. What is the single primary CTA?
3. Can anything be removed or moved behind disclosure?
4. Is the hierarchy obvious at a glance (title → key info → action)?
5. Any card-in-card nesting?
6. Only token typography, spacing, radii and semantic colors?
7. Dark mode checked?
8. 360 dp width and 1.3× text scale checked — no overflow?
9. Loading, empty and error states handled with the copy rules above?
10. Every value real? Demo content labelled?
11. Touch targets ≥ 48 dp, tooltips/semantics present, no color-only status?
12. Does it unmistakably look like CareerOS?
