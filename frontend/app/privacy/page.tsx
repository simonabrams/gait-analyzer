import type { Metadata } from "next";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Privacy Notice",
  description:
    "What Runlens collects, why, who processes it, and the controls you have over your videos and data.",
};

// Interim notice pending counsel review — see docs/trust/02-privacy-policy.md
// for the full scaffolding with [LEGAL REVIEW] markers. Keep every statement
// factually true of the running app; anything undecided is omitted rather than
// guessed at. PRIVACY_POLICY_VERSION (backend) should be bumped whenever this
// page's content materially changes.
const LAST_UPDATED = "August 27, 2026";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      {children}
    </section>
  );
}

const COLLECTED: Array<{ what: string; why: string }> = [
  {
    what: "Your videos (MP4/MOV) and the annotated videos and charts we generate",
    why: "They're the input and output of the analysis — we can't measure your form without them",
  },
  {
    what: "Your height",
    why: "Converts on-screen distances to real-world ones (stride length, bounce)",
  },
  {
    what: "Derived metrics: cadence, joint angles, stride and gait data",
    why: "The results we show you, and your progress over time",
  },
  {
    what: "Account info: email, name (via Clerk, our sign-in provider)",
    why: "Sign-in and account management",
  },
  {
    what: "Payment and subscription status (via Stripe)",
    why: "Billing — your card details go to Stripe and never touch our servers",
  },
  {
    what: "Usage analytics (via PostHog): pages viewed, features used",
    why: "To see what works and fix what doesn't",
  },
  {
    what: "Emails you send us, and referral codes",
    why: "Support, and crediting referrals",
  },
];

const SUBPROCESSORS: Array<{ name: string; purpose: string }> = [
  { name: "Clerk", purpose: "Sign-in and account management" },
  { name: "Vercel", purpose: "Website hosting" },
  { name: "Render", purpose: "API hosting and video processing" },
  { name: "Cloudflare R2", purpose: "Video and image storage" },
  { name: "Stripe", purpose: "Payments" },
  { name: "PostHog", purpose: "Product analytics" },
];

export default function PrivacyPage() {
  return (
    <div>
      <div className="max-w-3xl mx-auto px-6 py-16 space-y-10">
        <header className="space-y-4">
          <h1 className="text-3xl font-bold text-white">Privacy Notice</h1>
          <p className="text-sm text-gray-400">Last updated: {LAST_UPDATED}</p>
          <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 px-4 py-3 text-sm text-amber-200">
            This is an interim notice, currently under legal review. It describes —
            in plain language — how Runlens actually handles your data today, and it
            will be replaced with a reviewed version. Questions:{" "}
            <a href="mailto:hi@runlens.io" className="text-primary hover:underline">
              hi@runlens.io
            </a>
            .
          </div>
        </header>

        <div className="space-y-10 text-gray-300 text-sm leading-relaxed">
          <Section title="The short version">
            <ul className="list-disc pl-5 space-y-1.5">
              <li>We never sell your personal data.</li>
              <li>We never use your videos to train AI models.</li>
              <li>
                Nothing is shared publicly unless you share a run link or image
                yourself.
              </li>
              <li>
                Deleting a run removes its video, annotated video, charts, and
                metrics from our storage.
              </li>
            </ul>
          </Section>

          <Section title="What we collect, and why">
            <div className="rounded-xl border border-white/10 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-white/5 border-b border-white/10">
                    <th className="text-left px-4 py-2.5 text-gray-300 font-medium">What</th>
                    <th className="text-left px-4 py-2.5 text-gray-300 font-medium">Why</th>
                  </tr>
                </thead>
                <tbody>
                  {COLLECTED.map((row, i) => (
                    <tr
                      key={row.what}
                      className={`border-b border-white/5 align-top ${i % 2 === 0 ? "" : "bg-white/[0.02]"}`}
                    >
                      <td className="px-4 py-2.5 text-white">{row.what}</td>
                      <td className="px-4 py-2.5 text-gray-400">{row.why}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              That&apos;s the whole list — no location tracking, no contacts, no
              background collection.
            </p>
          </Section>

          <Section title="A note on video and body data">
            <p>
              Analyzing your running form means processing footage of your body and
              computing measurements from it (like joint angles and stride length).
              We treat this as the most sensitive data we hold: we ask for your
              explicit consent before your first upload, we record when you gave it
              and to which version of this notice, and we won&apos;t accept uploads
              without it. If this notice materially changes, we&apos;ll ask you to
              review and accept the new version before your next upload.
            </p>
          </Section>

          <Section title="Using Runlens without an account">
            <p>
              You can try Runlens once without signing up. When you do, we identify
              you by a random ID generated in your browser and stored there (not by
              your name or email) — it&apos;s just enough to give you one free scan
              and to know which run is yours.
            </p>
            <p>
              Everything else works the same way: we still ask you to confirm
              you&apos;re 18 or older and agree to this notice before we&apos;ll
              process your video, and your video and results are stored and
              protected exactly like a signed-in user&apos;s.
            </p>
            <p>
              The trade-off is that without an account, we have no way to help you
              get back to a scan you didn&apos;t save the link to — there&apos;s no
              run history and no &quot;forgot password&quot; recovery for a random
              browser ID. Bookmark your results page if you want to find it again.
            </p>
            <p>
              You can delete an anonymous scan yourself, anytime, right from its
              results page — no account needed. And if you sign up afterward, we
              link any scan(s) you made anonymously to your new account, so they
              show up in your run history instead of being orphaned.
            </p>
          </Section>

          <Section title="How your video flows">
            <p>
              You upload a video over an encrypted connection. Our servers analyze
              it — a computer-vision model tracks your joints frame by frame and
              computes your metrics. The video, its annotated version, and your
              results are stored in access-controlled cloud storage and served only
              through short-lived signed links. Processing happens on our servers,
              not on your device — we&apos;d rather tell you that plainly than imply
              otherwise.
            </p>
          </Section>

          <Section title="Who processes data on our behalf">
            <div className="rounded-xl border border-white/10 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-white/5 border-b border-white/10">
                    <th className="text-left px-4 py-2.5 text-gray-300 font-medium">Service</th>
                    <th className="text-left px-4 py-2.5 text-gray-300 font-medium">Purpose</th>
                  </tr>
                </thead>
                <tbody>
                  {SUBPROCESSORS.map((row, i) => (
                    <tr
                      key={row.name}
                      className={`border-b border-white/5 ${i % 2 === 0 ? "" : "bg-white/[0.02]"}`}
                    >
                      <td className="px-4 py-2.5 text-white">{row.name}</td>
                      <td className="px-4 py-2.5 text-gray-400">{row.purpose}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              These providers process data only to run Runlens. We don&apos;t sell
              your personal data to anyone, and we may disclose data if the law
              requires it.
            </p>
          </Section>

          <Section title="Sharing and public links">
            <p>
              Every run has a results page reachable by a long, unguessable link.
              It&apos;s not listed anywhere — but anyone you give the link to can
              see that run&apos;s annotated video, metrics, and charts. They cannot
              see your name, email, raw (unannotated) upload, or other runs.
              Deleting the run disables the link.
            </p>
          </Section>

          <Section title="How long we keep your data">
            <p>
              Your videos and results are kept until you delete them — there&apos;s
              no automatic expiry, so your run history is there when you come back.
              Deleting a run removes its video, annotated video, charts, and metrics
              from our storage. Consent records are kept as an audit log. Billing
              records are retained as required for accounting.
            </p>
          </Section>

          <Section title="Your controls">
            <ul className="list-disc pl-5 space-y-1.5">
              <li>
                <strong className="text-white">Delete any run</strong> — from your
                Runs page, anytime. Used Runlens without an account? Delete that
                scan directly from its results page instead — see above.
              </li>
              <li>
                <strong className="text-white">Delete everything</strong> — email{" "}
                <a href="mailto:hi@runlens.io" className="text-primary hover:underline">
                  hi@runlens.io
                </a>{" "}
                from your account&apos;s email address and we&apos;ll delete your
                account and all associated runs, videos, and results within 30
                days.
              </li>
              <li>
                <strong className="text-white">Get a copy of your data</strong> —
                email us and we&apos;ll send you what we hold about you.
              </li>
            </ul>
          </Section>

          <Section title="Security">
            <p>
              Data moves over encrypted connections (TLS). Videos and images live in
              access-controlled storage and are served via signed URLs that expire
              within an hour. Payments are handled end-to-end by Stripe, a
              PCI-DSS-compliant processor — card numbers never touch our servers.
            </p>
          </Section>

          <Section title="Age">
            <p>
              Runlens is for adults: you must be at least 18 to use Runlens. We ask
              every user — signed in or not — to confirm this before their first
              scan is processed. We don&apos;t knowingly collect data from anyone
              younger; if we learn we have, we&apos;ll delete it.
            </p>
          </Section>

          <Section title="Changes to this notice">
            <p>
              We&apos;ll post updates here with a new &quot;last updated&quot; date.
              For material changes, we&apos;ll ask you to review and re-accept
              before your next upload.
            </p>
          </Section>

          <Section title="Contact">
            <p>
              <a href="mailto:hi@runlens.io" className="text-primary hover:underline">
                hi@runlens.io
              </a>
            </p>
          </Section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
