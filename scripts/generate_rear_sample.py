"""Regenerate backend/schema/sample_run_both_views.json — a results document for
a run with BOTH a side and a rear video — from the real pipeline code
(job_runner.apply_confidence_gate for the side view, rear_metrics.compute_rear_metrics
for the rear view on synthetic landmarks).

    python scripts/generate_rear_sample.py

The output is validated against backend/schema/results.schema.json by
backend/tests/test_results_schema.py. Regenerate after changing either module
or the schema. The side `strides` list holds 3 entries for readability (the real
list has one per stride; the schema places no limit on it).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import results_schema  # noqa: E402
from backend.job_runner import apply_confidence_gate  # noqa: E402
from backend.rear_metrics import compute_rear_metrics  # noqa: E402
from backend.tests.rear_fixtures import FPS, make_rear_frames  # noqa: E402

OUT = ROOT / "backend" / "schema" / "sample_run_both_views.json"


def _side_results():
    """A plausible completed side-view result. Built from realistic values (the
    shape compute_metrics produces) rather than from synthetic landmarks, which
    don't reliably clear the side confidence gate; the gate itself and the
    heuristics are the real ones."""
    strides = [
        {
            "cadence": 171.4 + d,
            "vertical_osc_cm": 8.1,
            "knee_angle_strike_deg": 21.5,
            "foot_strike_position_cm": 6.2,
            "trunk_lean_deg": 5.4,
            "duration_sec": 0.7,
            "stride_num": k + 1,
            "start_frame": 10 + 21 * k,
            "end_frame": 31 + 21 * k,
        }
        for k, d in enumerate((0.0, -0.4, 0.3))
    ]
    results = {
        "meta": {
            "height_cm": 175,
            "video_file": "input.mp4",
            "analyzed_at": "2026-09-21T12:00:00+00:00",
            "fps": 30.0,
            "num_frames": 451,
        },
        "summary": {
            "cadence_avg": 171,
            "vertical_osc_avg_cm": 8,
            "knee_angle_strike_avg_deg": 22,
            "foot_strike_position_avg_cm": 6,
            "trunk_lean_avg_deg": 5,
            "num_strides": 20,
            "num_strides_detected": 20,
            "cadence_confidence": 0.883,
        },
        "flags": [],
        "strides": strides,
    }
    _, results = apply_confidence_gate(results)
    return results


def build():
    side = _side_results()

    # Rear view: a separate recording, different length, starting mid-cycle, with
    # a left/right hip-drop and valgus difference so the asymmetry fields are populated.
    rear_frames = make_rear_frames(
        n_frames=330,
        start_phase=0.37,
        hip_drop_left=4.0,
        hip_drop_right=11.0,
        valgus_left=5.0,
        valgus_right=15.0,
        pronation_left=6.0,
        pronation_right=8.0,
    )
    rear = compute_rear_metrics(rear_frames, FPS, video_file="rear.mp4")
    return results_schema.attach_rear_view(side, rear)


if __name__ == "__main__":
    doc = build()
    OUT.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} (schema_version={doc['schema_version']}, rear status={doc['rear_view']['status']})")
