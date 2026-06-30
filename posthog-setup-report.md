<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into the Runlens FastAPI backend. A `Posthog` client instance is initialized at module startup in both `backend/main.py` (API server) and `backend/worker.py` (Celery worker), reading credentials from environment variables. Five key business events are now captured across the full video analysis lifecycle — from initial upload through processing completion or failure, plus sharing and deletion signals. The `posthog` package has been added to `backend/requirements.txt` and `POSTHOG_PROJECT_TOKEN`/`POSTHOG_HOST` have been written to `.env`.

| Event | Description | File |
|-------|-------------|------|
| `run_created` | User uploads a video and a new analysis run is created. | `backend/main.py` |
| `run_completed` | Worker successfully finishes processing a video run. | `backend/worker.py` |
| `run_failed` | Worker encounters an error processing a video run. | `backend/worker.py` |
| `run_viewed` | A run detail page is fetched (public endpoint, supports sharing). | `backend/main.py` |
| `run_deleted` | Authenticated user deletes their run and associated R2 assets. | `backend/main.py` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- [Analytics basics (wizard) — Dashboard](https://us.posthog.com/project/492067/dashboard/1779519)
- [Runs created over time](https://us.posthog.com/project/492067/insights/BGtvlwDJ)
- [Run completion funnel](https://us.posthog.com/project/492067/insights/PEgHroku)
- [Run failures over time](https://us.posthog.com/project/492067/insights/0EabRr9Q)
- [Runs viewed (sharing activity)](https://us.posthog.com/project/492067/insights/xuhFYgt8)
- [Runs deleted over time](https://us.posthog.com/project/492067/insights/F7krBn2X)

## Verify before merging

- [ ] Run a full production build (the wizard only verified the files it touched) and fix any lint or type errors introduced by the generated code.
- [ ] Run the test suite — call sites that were rewritten or instrumented may need updated mocks or fixtures.
- [ ] Add `POSTHOG_PROJECT_TOKEN` and `POSTHOG_HOST` to `.env.example` and any deployment bootstrap scripts (e.g. `render.yaml` environment config) so collaborators and CI know what to set.
- [ ] Confirm the returning-visitor path also calls `identify` — the current integration uses the Clerk `user_id` as `distinct_id` on every event, but if you want richer person profiles (name, email, etc.) you should call `posthog_client.set(distinct_id=user_id, properties={...})` at login time to associate them.

### Agent skill

We've left an agent skill folder in your project. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
