# Trust & Privacy — Gap Analysis (as of 2026-07-25)

Where Runlens stands against the trust-content outline: what exists, what's
missing, and the engineering work hiding behind the copy. Ordered roughly by
launch-blocker severity.

## What already exists (real assets — don't rebuild)

- **Per-run deletion that actually purges storage** — `DELETE /api/runs/{id}`
  removes the raw video, annotated video, and dashboard image from R2 plus the
  DB row (`backend/main.py:492`). This is the single most trust-defining
  control per the outline, and it substantially works (caveat: gap #7).
- **Medical disclaimer, everywhere** — footer on every page
  (`components/Footer.tsx`) + a strong "What Runlens is not" section on
  `/about`.
- **Accuracy honesty** — `/about` has genuinely good limitations content
  (vision vs. accelerometers, environmental factors, "directional insights not
  clinical measurements", the running-coach anecdote), plus the dismissible
  `AccuracyBanner` on run pages.
- **Confidence plumbing** — `cadence_confidence` (0–1) computed in
  `backend/heuristics.py` with a low-confidence flag; per-landmark visibility
  from MediaPipe is available for more of this.
- **Sound security posture to describe** — Clerk RS256 JWT auth, 1-hour
  presigned R2 URLs, ownership checks (404 not 403), Stripe for payments,
  rate limiting.
- **Raw video is never exposed** — public run detail returns only annotated
  video + dashboard; the raw upload has no public read path.

## Gaps

### 1. No legal documents — INTERIM VERSIONS LIVE 2026-07-25, counsel review pending
Interim `/privacy` (plain-language notice) and `/terms` pages are built and
linked from the footer, both banner-labeled as under legal review and written
to state only what is true of the app today (no entity name, no governing-law
clause — omitted rather than guessed). Remaining: counsel review (the full
scaffolding with markers is `02-privacy-policy.md`), legal entity naming, and
the [DECIDE] on age minimum (interim pages say 18).

### 2. ~~No consent flow, no consent logging~~ — BUILT 2026-07-25
`ConsentModal` gates the first upload; consent is logged in `consent_records`
(user_id, policy_version, timestamp — migration 008) and enforced server-side
by `POST /api/runs` (403 `consent_required`). Bumping `PRIVACY_POLICY_VERSION`
forces re-consent (covers gap 11's re-consent item). Remaining: the modal's
checkbox wording needs counsel sign-off, and it links to `/privacy` and
`/terms` which don't exist yet (gap 1) — ship those before deploying this.

### 3. No public Trust & Privacy page
Nothing sells the (genuinely decent) trust posture.
→ Draft: `01-trust-privacy-page.md`, target `/trust`, link from footer.

### 4. No stated or enforced retention policy
Raw videos live in R2 indefinitely. Nothing anywhere tells users how long
footage is kept. The outline's "concrete retention window" trust claim
requires either honest "until you delete it" copy or a retention job
(auto-delete raw video N days post-processing — annotated video is what the
product actually serves afterward).

### 5. ~~Account deletion doesn't exist end-to-end~~ — CASCADE BUILT 2026-07-25
`POST /api/webhooks/clerk` (Svix-verified, `CLERK_WEBHOOK_SECRET`) handles
`user.deleted`: deletes all runs storage-first (R2 objects, then DB rows),
plus the subscription row; consent records are kept as audit trail; Svix
retries are the reconciliation loop for partial failures. `/privacy` also
documents a manual path (email from account address → full deletion within
30 days). Remaining: an in-app "delete account" button (Clerk profile or
custom UI) so deletion is self-serve, PostHog person deletion, and the
counsel questions (Stripe customer record, consent-record survival).

### 6. Analytics runs with no consent — body data REMOVED 2026-07-25
`height_cm` (and `cadence_avg`) no longer sent to PostHog from any event
(frontend uploader, backend run_created, worker run_completed/run_failed) —
analytics now carries product-usage signals only, matching /privacy's "pages
viewed, features used". Remaining: PostHog still initializes unconditionally
and identifies users by Clerk ID with no cookie/consent banner — consent
basis for EU visitors is a **[LEGAL REVIEW]** question.

### 7. ~~Run deletion is best-effort against storage~~ — FIXED 2026-07-25
`storage.delete_object` previously swallowed every failure (`except: pass`),
making deletion promises unverifiable. It now raises, and `delete_run`
returns 502 without touching the DB row when storage deletion fails, so the
user can retry (retries are idempotent: S3 deletes of absent keys succeed).
The Clerk cascade uses the same storage-first rule with Svix retries as the
reconciliation loop. The deletion promise on /privacy is now true.

### 8. Public-by-link run pages are undisclosed
`/runs/[id]` is intentionally public (sharing), but nothing tells the owner
that their result page — including the annotated video of them — is viewable
by anyone with the link, and there's no visibility toggle. Minimum: the
disclosure microcopy (`03-in-app-copy.md` #8). Better: per-run
public/private flag.

### 9. No data export
No endpoint or UI. Fine to sequence post-launch per the outline, but the
rights section of the policy (§12) references it — keep the [CONFIRM] marker
until built.

### 10. No age gate / minors stance
Nothing in sign-up or copy addresses minimum age. **[DECIDE + LEGAL REVIEW]**

### 11. Smaller items
- AI-training stance ("we don't train on your video") is true but stated
  nowhere — it's a high-stakes FAQ answer; publish it.
- ~~No re-consent mechanism on policy change~~ — built with gap #2: bumping
  `PRIVACY_POLICY_VERSION` forces the consent modal at the next upload.
  Optional polish: a post-sign-in interstitial + plain-English changelog.
- `preprocessing_meta` (trimming, fps) isn't surfaced as per-run "what the
  camera couldn't see" limitations — the data exists; it's a UI gap.
- Outline's "on-device processing" wedge is **not true today** (cloud
  pipeline on Render) — all copy in this folder is worded for cloud; don't
  let marketing drift toward on-device claims.
- Affiliate/shoe-rec copy is drafted but must ship *with* that feature, never
  after.

## Minimum viable trust for public launch (per outline, mapped to Runlens)

1. Privacy policy + ToS linked in footer & sign-up (gap 1) — ✅ interim
   versions live 2026-07-25; **counsel review still required**
2. ~~First-upload consent + consent logging (gap 2)~~ ✅ built 2026-07-25;
   checkbox wording still needs counsel sign-off
3. Medical disclaimer at first result (copy exists; placement tweak)
4. ~~Account deletion cascade + working per-run delete~~ ✅ built/fixed
   2026-07-25 (gaps 5, 7); manual path documented on /privacy
5. Analytics consent decision (gap 6) — body data removed ✅; EU consent
   basis still open for counsel

Everything else — trust page polish, export, retention automation, sharing
toggle — can follow shortly after.
