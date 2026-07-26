import type { Metadata } from "next";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The terms that govern your use of Runlens.",
};

// Interim terms pending counsel review — see docs/trust/. Keep every statement
// factually true of the running app; anything undecided is omitted rather than
// guessed at.
const LAST_UPDATED = "July 25, 2026";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      {children}
    </section>
  );
}

export default function TermsPage() {
  return (
    <div>
      <div className="max-w-3xl mx-auto px-6 py-16 space-y-10">
        <header className="space-y-4">
          <h1 className="text-3xl font-bold text-white">Terms of Service</h1>
          <p className="text-sm text-gray-400">Last updated: {LAST_UPDATED}</p>
          <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 px-4 py-3 text-sm text-amber-200">
            This is an interim version of our terms, currently under legal review. It
            reflects how Runlens actually works today and will be replaced with a
            reviewed version. Questions:{" "}
            <a href="mailto:hi@runlens.io" className="text-primary hover:underline">
              hi@runlens.io
            </a>
            .
          </div>
        </header>

        <div className="space-y-10 text-gray-300 text-sm leading-relaxed">
          <Section title="1. The agreement">
            <p>
              These terms are an agreement between you and Runlens (&quot;we&quot;,
              &quot;us&quot;). By creating an account or uploading a video, you agree to
              them and to our <a href="/privacy" className="text-primary hover:underline">Privacy Notice</a>.
              If you don&apos;t agree, please don&apos;t use Runlens.
            </p>
          </Section>

          <Section title="2. What Runlens is — and isn't">
            <p>
              Runlens analyzes running videos with computer vision and gives you
              form metrics and training feedback. It is a <strong>fitness and
              educational tool, not a medical device</strong>. It does not diagnose,
              treat, or prevent any injury or condition, and its feedback is not
              medical advice. If you have pain or an injury, see a qualified
              professional — a physical therapist or sports doctor can assess things
              no camera can.
            </p>
            <p>
              Metrics are estimates derived from video. They are affected by camera
              angle, lighting, frame rate, and clothing, and are best used as
              directional trends — not clinical measurements. We don&apos;t guarantee
              their accuracy, and you use them at your own judgment.
            </p>
          </Section>

          <Section title="3. Your account">
            <p>
              You must be at least 18 years old to use Runlens. Keep your sign-in
              credentials secure; you&apos;re responsible for activity on your
              account.
            </p>
          </Section>

          <Section title="4. Your content">
            <p>
              You own the videos you upload and the results generated from them. You
              give us the limited permission we need to operate the service: to
              store, process, and analyze your videos, and to display your videos
              and results back to you and to anyone you share a run link with. We
              don&apos;t use your videos for anything else — including training AI
              models — and this permission ends for content you delete.
            </p>
            <p>
              Only upload footage you have the right to upload. Film yourself; if
              other people are clearly identifiable in the frame, get their OK
              first.
            </p>
          </Section>

          <Section title="5. Sharing">
            <p>
              Each run has a results page reachable by a long, unguessable link.
              Anyone you give that link to can view that run&apos;s annotated video
              and metrics (not your name, email, or other runs). Deleting the run
              disables the link.
            </p>
          </Section>

          <Section title="6. Acceptable use">
            <p>
              Don&apos;t misuse the service: no uploading footage of others without
              their consent, no unlawful content, no attempts to break, overload,
              scrape, or reverse-engineer the service, and no reselling analysis
              results as your own service.
            </p>
          </Section>

          <Section title="7. Subscriptions and payments">
            <p>
              Paid plans are billed through Stripe and renew automatically until
              cancelled. You can cancel anytime from your account&apos;s billing
              page; cancellation takes effect at the end of the current billing
              period. Free-tier limits (such as the number of included scans) are
              shown in the app and may change.
            </p>
          </Section>

          <Section title="8. Disclaimers">
            <p>
              Runlens is provided <strong>&quot;as is&quot; and &quot;as
              available&quot;, without warranties of any kind</strong>, express or
              implied — including fitness for a particular purpose, accuracy, and
              uninterrupted availability. Running involves inherent risk of injury;
              decisions about your training are yours.
            </p>
          </Section>

          <Section title="9. Limitation of liability">
            <p>
              To the maximum extent permitted by law, we are not liable for
              indirect, incidental, special, or consequential damages, or for lost
              profits or data, arising from your use of Runlens. Our total
              liability for any claim is limited to the amount you paid us in the
              twelve months before the claim arose (or US $50 if you have paid us
              nothing).
            </p>
          </Section>

          <Section title="10. Termination">
            <p>
              You can stop using Runlens at any time and request deletion of your
              account and data (see the Privacy Notice). We may suspend or close
              accounts that violate these terms.
            </p>
          </Section>

          <Section title="11. Changes to these terms">
            <p>
              We&apos;ll post updates here with a new &quot;last updated&quot; date.
              For material changes we&apos;ll notify you in the app. Continuing to
              use Runlens after a change means you accept the updated terms.
            </p>
          </Section>

          <Section title="12. Contact">
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
