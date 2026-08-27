# Layer 3 — In-App Consent, Disclaimers & Data Controls (draft microcopy)

> Just-in-time trust moments. Each block = one screen or piece of microcopy,
> with where it goes and its current implementation status.
> DRAFT — consent and disclaimer wording needs counsel review before shipping.

---

## 1. First-upload consent (BUILT 2026-07-25, anon age checkbox added 2026-08-27 — copy pending legal review)

**Where:** `ConsentModal`, shown on the first Analyze click (and whenever
`PRIVACY_POLICY_VERSION` is bumped). Consent is logged server-side in
`consent_records` (user, policy version, age confirmation if anonymous,
timestamp) and enforced by `POST /api/runs` (403 `consent_required`). The
modal links to `/privacy` and `/terms`, which **do not exist yet** — those
pages must ship before this does.

> ### Before your first analysis
>
> To analyze your form, Runlens uploads your video to our servers, where a
> computer-vision model measures your movement (cadence, joint angles, stride).
> Your video and results stay in your account until you delete them — and
> deleting a run removes them from our storage.
>
> We never sell your data or use your video to train AI.
>
> ☐ I've read and agree to the [Privacy Policy](/privacy) and
> [Terms](/terms), and I consent to Runlens processing my video and the
> body-movement measurements derived from it.
>
> ☐ *(anonymous visitors only)* I'm 18 or older.
>
> **[Agree & continue]**  ·  [Not now]

**Anonymous-only age checkbox (BUILT 2026-08-27):** shown only when there's no
Clerk session — a signed-in user has no equivalent prompt today (account
creation is assumed to imply it; see gap analysis #10 — that assumption itself
isn't enforced anywhere and remains open). Both checkboxes are required to
continue. `POST /api/consent` rejects anonymous consent missing the
confirmation (400 `age_confirmation_required`) — this is enforced
server-side, not just gated in the UI. Persisted as `age_confirmed` on the
`consent_records` row (null for authenticated consent, where it isn't
collected).

**[LEGAL REVIEW — the checkbox sentence is the load-bearing consent language,
especially re: biometric-derived data. Counsel decides if it must be a
separate, explicit consent distinct from ToS acceptance. The age checkbox
wording ("I'm 18 or older") is a self-attestation, not verified age
assurance — counsel should confirm this is sufficient for the jurisdictions
Runlens serves.]**

## 2. Filming-others reminder (NOT BUILT)

**Where:** Small persistent line under the dropzone in `VideoUploader`.

> Film yourself — and if friends or club-mates are clearly in frame, get their
> OK before uploading.

## 3. Medical disclaimer at first result (PARTIAL)

**Current state:** footer on every page says "Not medical advice. For fitness
and educational purposes only." The dismissible `AccuracyBanner` on the run
page covers *accuracy*, not the medical boundary.

**Change:** extend the first-view banner (or add a sibling line) so the first
result a user ever sees carries the medical boundary, then stays one tap away
(link to /trust#coach-not-clinic).

> Runlens gives training feedback, not medical diagnosis. If you're dealing
> with pain or injury, a physio or sports doctor should be your first stop —
> not an app. [More on what Runlens can and can't tell you →](/trust)

## 4. Pain/injury pathway (NOT BUILT — depends on a pain input existing)

**Where:** If/when the product asks about pain or a user flags discomfort.
Until such an input exists, the closest hook is heuristics feedback cards.

> Some of what you're describing may be worth a professional's eyes. A
> physical therapist can assess things no camera can — this isn't us dodging,
> it's genuinely the right tool for pain.

## 5. Affiliate disclosure at recommendation (FUTURE — ship WITH shoe recs, not after)

**Where:** Inline, immediately adjacent to every shoe recommendation/link.
FTC-style: clear, conspicuous, near the link — not only in the policy.

> **Why this shoe:** your gait shows [reason, e.g. "a midfoot strike with
> higher-than-typical bounce"], and this model's [attribute] suits that.
>
> *We may earn a commission if you buy through this link. Commissions never
> affect which shoes we recommend.*

Ideally include one non-affiliate alternative per recommendation slot.
**[LEGAL REVIEW — FTC disclosure wording]**

## 6. Confidence & limitations on results (PARTIAL)

**Current state:** backend computes `cadence_confidence` and heuristics emit a
low-confidence flag; `AccuracyBanner` gives general limitations. Missing: an
explicit per-run "what the camera couldn't see this time" note tied to actual
conditions (low ankle visibility, trimming, low fps from `preprocessing_meta`).

**Microcopy pattern:**

> **Heads up on this run:** [ankle tracking was intermittent / the video was
> trimmed to 3 min / low frame rate], so [cadence] is lower-confidence than
> usual. Trends across runs are still meaningful; treat single numbers loosely.

## 7. Deletion confirmations (PARTIAL — per-run delete exists)

**Delete a run:**

> Delete this run? The video, annotated video, dashboard, and metrics will be
> removed from our storage, and any share link will stop working. This can't
> be undone.

**Anonymous scans (BUILT 2026-08-27):** `DeleteScanButton` on the run detail
page gives an anonymous visitor the same deletion control, without an
account or a Runs page to find it from. It renders only when the viewing
browser's `localStorage` remembers creating that specific run (see
`lib/anon.ts`'s `rememberAnonRun`/`hasAnonRun`) — never for other visitors of
a shared link. `DELETE /api/runs/{id}` now accepts `X-Anon-Id` the same way
`create_run`/consent do, and checks it against the run's owner id — same
404-not-403 ownership check as the authenticated path. Currently a plain
confirm/cancel toggle, not the fuller copy above — **[FOLLOW-UP: bring this
in line with the confirmation copy once counsel reviews it]**.

**Delete account (backend cascade BUILT 2026-07-25 via Clerk `user.deleted`
webhook; manual email path documented on /privacy. This confirmation copy is
for the future in-app button):**

> Delete your Runlens account? All of your runs — videos, results, history —
> will be permanently deleted, along with your account details. Active
> subscriptions are cancelled. This can't be undone.

## 8. Sharing transparency (NOT BUILT)

**Where:** Next to `ShareButton` on the run detail page; also a one-time note
the first time a user copies a link.

> Anyone with this link can view this run — the annotated video and metrics,
> but not your name, email, or other runs. Deleting the run disables the link.

**Share-image note (first use):**

> The image includes your metrics and score — check it before posting. It
> doesn't include your name. **[CONFIRM against share-card contents]**

## 9. Settings → Privacy & Data surface (NOT BUILT)

A single place listing: export my data · delete all runs · delete account ·
marketing/analytics opt-out **[DECIDE: whether analytics becomes opt-in/out —
see gap analysis #6]** · links to /trust and /privacy. The controls it exposes
must exist before the screen does.

## 10. Re-consent on material policy change (BUILT 2026-07-25 — at upload, not sign-in)

**How it works today:** consent is per policy version. Bumping the
`PRIVACY_POLICY_VERSION` env var makes everyone's consent stale, so the
consent modal (#1) reappears at the next upload attempt, and the server
refuses uploads until the new version is accepted. Each acceptance is a new
`consent_records` row — the old one is kept as audit trail.

**Optional enhancement (not built):** a one-time interstitial after sign-in —
catches users before they reach the upload flow — plus a plain-English
changelog:

> We've updated our Privacy Policy — here's [what changed](/privacy#changelog)
> in plain English. Please take a look and re-accept to keep using Runlens.
