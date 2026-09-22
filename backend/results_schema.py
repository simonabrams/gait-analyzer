"""
Versioning of the results JSON and the read-time merge of the rear view into it.

Schema versions (full JSON Schema: backend/schema/results.schema.json):
  1  Side-view only: {meta, summary, flags, strides}. Every run created before
     the rear view existed. These documents carry NO `schema_version` key, so
     "absent" means 1 — existing runs stay valid with no migration and no
     backfill.
  2  Version 1 plus an optional top-level `rear_view` object (see
     backend/rear_metrics.py). A document with a `rear_view` must say
     schema_version 2; a document without one may say 1 or 2 (or nothing).

Where the data lives: the side pipeline keeps writing `runs.results_json`
whole (worker._finalize_run), and the rear pipeline writes its own
`run_videos.results_json` for the rear row. Two independent tasks writing one
JSONB column would lose an update, so the two are merged here, at read time,
instead of by either writer.
"""

SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1

# Statuses a rear_view can carry before/without an analysis: while the rear
# task is queued or running, and if it crashed. Real analyses carry the
# rear_confidence gate status ("ok" | "low_confidence" | "insufficient_data").
REAR_PROCESSING = "processing"
REAR_FAILED = "failed"


def schema_version_of(results: dict | None) -> int:
    """Version of a stored results document; absent means the legacy v1."""
    if not results:
        return LEGACY_SCHEMA_VERSION
    return results.get("schema_version", LEGACY_SCHEMA_VERSION)


def rear_view_from_video_row(row) -> dict | None:
    """The `rear_view` object for a run_videos row with view_type 'rear' (or
    None if the run has no rear video). Pipeline state (processing / failed)
    is mapped onto the same object so consumers only look in one place.

    Never exposes the raw exception text stored in error_message: the rear
    view is part of the public, shareable run response.
    """
    if row is None:
        return None
    if row.status == "complete" and row.results_json:
        return row.results_json
    if row.status == "failed":
        return {"status": REAR_FAILED, "error": "rear_analysis_failed"}
    return {"status": REAR_PROCESSING}


def attach_rear_view(results: dict | None, rear_view: dict | None) -> dict | None:
    """Return `results` with `rear_view` attached and schema_version set to 2.
    Returns `results` unchanged (same object, still v1 if it was) when there is
    no rear view, and also when there are no side results yet: the rear view is
    additive and never turns a still-processing side run into a "has results"
    one for clients that key off `results` being non-null."""
    if not results or rear_view is None:
        return results
    return {**results, "schema_version": SCHEMA_VERSION, "rear_view": rear_view}
