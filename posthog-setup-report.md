<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into the Runlens gait analysis app. The backend FastAPI app already had a solid foundation (`posthog_client` initialized using the `Posthog()` class constructor, five key lifecycle events tracked across `main.py` and `worker.py`, and exception autocapture enabled). This run extended that with a full frontend integration: a `PostHogProvider` component for the Next.js App Router, automatic user identification via Clerk, client-side pageview tracking for client-side navigation, and four new event capture calls in the upload and share flows. Environment variables were written to both `.env` (backend) and `frontend/.env.local` (frontend).

| Event name | Description | File |
|---|---|---|
| `run_created` | User uploads a video and creates a new gait analysis run | `backend/main.py` |
| `run_viewed` | A user views a completed run's results page | `backend/main.py` |
| `run_deleted` | User deletes a run from their history | `backend/main.py` |
| `run_completed` | Video analysis processing completed successfully | `backend/worker.py` |
| `run_failed` | Video analysis processing failed due to an error or timeout | `backend/worker.py` |
| `analysis_submitted` | User clicks Analyze to submit a video file for processing | `frontend/components/VideoUploader.tsx` |
| `upload_failed` | Video upload or processing failed on the client side | `frontend/components/VideoUploader.tsx` |
| `share_link_copied` | User copies the shareable link for a run result | `frontend/components/ShareButton.tsx` |
| `share_image_downloaded` | User shares or downloads the run result image card | `frontend/components/ShareButton.tsx` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- [Analytics basics (wizard) dashboard](https://us.posthog.com/project/492067/dashboard/1781912)
- [Runs created over time](https://us.posthog.com/project/492067/insights/OZRnY88P)
- [Run completion vs failure rate](https://us.posthog.com/project/492067/insights/FABdCXIt)
- [Analysis submission to completion funnel](https://us.posthog.com/project/492067/insights/ZhHqRaAY)
- [Share activity](https://us.posthog.com/project/492067/insights/HxVcmFL3)
- [Unique active users (run creators)](https://us.posthog.com/project/492067/insights/JHdpv0EV)

## Verify before merging

- [ ] Run a full production build (the wizard only verified the files it touched) and fix any lint or type errors introduced by the generated code.
- [ ] Run the test suite — call sites that were rewritten or instrumented may need updated mocks or fixtures.
- [ ] Add `POSTHOG_PROJECT_TOKEN` and `POSTHOG_HOST` to `.env.example`, and `NEXT_PUBLIC_POSTHOG_KEY` and `NEXT_PUBLIC_POSTHOG_HOST` to `frontend/.env.local.example`, so collaborators know what to set.
- [ ] Confirm the returning-visitor path also calls `identify` — the `UserIdentifier` component in `PostHogProvider.tsx` fires on every render when a user is signed in via Clerk, so returning sessions should be covered, but verify in PostHog that person profiles are being created correctly.

### Agent skill

We've left an agent skill folder in your project. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
