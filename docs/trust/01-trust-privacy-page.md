# Layer 1 — Public "Trust & Privacy" Page (draft copy)

> Target route: `/trust` (linked from footer, upload area, and run detail pages).
> Marketing-grade, human, skimmable. DRAFT — review with counsel before publishing.
>
> Markers: **[DECIDE]** = product decision needed · **[CONFIRM]** = verify the
> claim is true before publishing · **[LEGAL REVIEW]** = counsel must approve.

---

## Hero

**Your run. Your data. Honest feedback.**

Runlens analyzes your running form from a short video. That means you trust us
with footage of you — so here's exactly what we do with it, what we never do,
and the controls you have. No legalese, no fine print games.

---

## Your video, your data

**What we never do:**

- We **never sell** your personal data. Not your video, not your metrics, not
  your email.
- We **never post** your video or results anywhere. Sharing only happens when
  *you* share a link or image.
- We **never use your video to train AI models.** Our pose tracking uses a
  pre-trained model (MediaPipe); your footage is analyzed, not learned from.
  **[CONFIRM — this must stay true, or this line must change before it stops being true]**
- We **never share raw video with third parties** for their own use — brands,
  advertisers, anyone.

**What we collect, and why:**

| What | Why |
|---|---|
| Your video (MP4/MOV, side view) | It's the input — we can't analyze your form without it |
| Your height | Converts pixels to real-world distances (stride length, bounce) |
| Derived metrics (cadence, joint angles, stride data) | The results we show you and your progress over time |
| Account info (email, name — via Clerk) | Sign-in and account management |
| Payment info (via Stripe) | Billing — card details go to Stripe, never to our servers |
| Usage analytics (via PostHog) | To see which features work and fix what doesn't |

That's it. No location tracking, no contacts, no background data collection.

---

## How your data flows

*(Add a simple diagram: Phone → Upload → Analysis → Your results)*

1. **You upload** a video over an encrypted connection (HTTPS).
2. **Our servers analyze it** — a computer-vision model tracks your joints frame
   by frame and computes your metrics. This happens in our cloud
   infrastructure; we're upfront that it's not on-device.
3. **We store** the video, the annotated version, and your metrics in secure
   cloud storage (Cloudflare R2), accessible only through short-lived signed
   links.
4. **You get results** — and everything stays in your account until you delete it.

**How long we keep things:** **[DECIDE — currently: until you delete the run.
Options: (a) state that honestly, (b) build auto-deletion of raw video N days
after processing and state the window. The outline recommends a concrete
window; "we delete your raw video 30 days after analysis unless you save it"
is a stronger trust claim but requires the retention job to exist first.]**

---

## You're in control

- **Delete any run** — removes the video, the annotated video, the dashboard,
  and the metrics from our storage. From your Runs page, in two taps.
- **Delete everything** — delete your account and all runs with it. *(Built
  2026-07-25: Clerk account deletion cascades through runs, videos, and
  subscription; interim manual path is email → deletion within 30 days.)*
- **Export your data** — get a copy of what we hold. *(Manual by email today;
  self-serve export is a future build — keep this bullet worded honestly.)*
- **Control sharing** — run pages are private-by-obscurity links; nothing is
  shared until you send the link or image. *(See "Sharing" below.)*

*(Show screenshots of where each control lives.)*

---

## Sharing: what's public and what isn't

When you share a run, you're sharing a **link**. Anyone with that link can see
that run's results page — the annotated video, the metrics, and the charts.
They cannot see your name, your email, your other runs, or your raw
(unannotated) video.

Run links are long random codes that can't be guessed, but a link is a link:
anyone you send it to can view it or pass it on. **Deleting the run kills the
link** — that's your revoke button.

The share **image** (scorecard) contains only: **[CONFIRM exact contents —
metrics, date, arc ring; no name/face? verify against share-card route]**.

---

## We're a coach, not a clinic

Runlens is a fitness tool, not a medical device. It can't diagnose injuries,
and it doesn't try to. Our feedback is training guidance — the kind you'd get
from a knowledgeable friend with a good eye, not from a physio with a
treatment plan.

**If something hurts, see a professional.** A physical therapist or sports
doctor can assess things no camera can. Runlens will never tell you to "run
through" pain — and if you're pain-free, you may not need to change anything
at all.

**[LEGAL REVIEW — wellness/medical-device positioning language]**

---

## How we make money (and why our advice is honest)

Runlens makes money one way today: **subscriptions.** You pay for analysis;
we're not in the business of monetizing your data.

**[FUTURE — activate when shoe recommendations ship:]** If we recommend a shoe
and you buy it through our link, we may earn a commission. Two promises:
(1) we tell you right there, next to the recommendation, and (2) commission
never affects what we recommend — recommendations are driven by *your gait
data*, and we'll always tell you *why* a shoe fits your form.
**[LEGAL REVIEW — FTC disclosure wording]**

---

## How accurate is it, really?

Honest answer: **good enough to be useful, not good enough to be clinical.**

- Runlens uses computer-vision pose tracking (MediaPipe) plus running-specific
  heuristics tuned against research-backed target ranges.
- Accuracy depends on your video: camera angle, lighting, frame rate, clothing,
  and motion blur all matter. [Our filming tips](/about) make a real difference.
- A single 2D side-view camera can't see everything — it can't measure ground
  reaction forces, and out-of-plane movement (like hip drop toward the camera)
  is invisible to it.
- When we're not confident, we say so: low-confidence measurements are flagged
  in your results rather than presented as fact.

Treat your numbers as **directional trends and session-to-session
comparisons** — the picture your watch can't show you — not lab measurements.

---

## How we keep it safe

- All data moves over encrypted connections (TLS).
- Videos and images live in access-controlled cloud storage and are served via
  short-lived signed URLs (they expire within an hour).
- Payments are handled end-to-end by Stripe, a PCI-DSS-compliant processor;
  card numbers never touch our servers.
- Access to production systems is limited to **[CONFIRM — who has access; keep
  truthful and non-specific]**.

---

## Kids & minors

Runlens is for adults. You must be at least **[DECIDE: 16 or 18 — align with
Clerk config, app-store rating if applicable, and counsel]** to create an
account. **[LEGAL REVIEW — COPPA/age-gating]**

---

## FAQ

**Do you use my video to train your AI?**
No. Our pose model is pre-trained; your video is analyzed and stored for you —
never used as training data. **[CONFIRM]**

**Who can see my video?**
You — and anyone you share a run link with (they see the annotated version,
not the raw upload). Our team can access stored files only for
**[DECIDE/CONFIRM: support and debugging policy — define and state it]**.

**Can I film at my running club or a race?**
The analysis works on you, but be mindful of others: if other people are
clearly in frame, get their OK before uploading. It's their footage too.

**What happens when I delete a run?**
The video, annotated video, dashboard image, and metrics are deleted from our
storage, and any share link stops working. *(True as of 2026-07-25 — gap #7
fixed; deletion fails loudly instead of proceeding on storage errors.)*

**What happens if I cancel my subscription?**
Your account and runs stay; you keep **[DECIDE — free-tier access rules after
cancellation]**.

**What happens to my data if I delete my account?**
All of your runs — videos, results, history — and your subscription record
are deleted automatically. Consent records are kept as an audit log
**[LEGAL REVIEW — confirm consent-record survival stance]**.

**Where is my data stored?**
**[CONFIRM — R2 bucket region / Render region; GDPR transfer implications for
EU users → legal policy §11.]**

**Do you comply with GDPR / CCPA?**
**[LEGAL REVIEW — do not answer this in copy until counsel signs off.]**

---

## Footer of this page

Questions about your data: **privacy@runlens.io** **[DECIDE — create this
alias, or use hi@runlens.io]** · [Privacy Policy](/privacy) ·
[Terms of Service](/terms)
