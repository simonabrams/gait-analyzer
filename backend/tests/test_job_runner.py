"""Unit tests for backend.job_runner.apply_confidence_gate — the single
choke point that decides whether a computed result is trustworthy enough to
report/coach on. No video/pose I/O: this operates on an already-computed
metrics.compute_metrics()-shaped dict, which is what makes it unit-testable
without a real pipeline run."""
from backend.job_runner import apply_confidence_gate


def _results(
    num_strides=20,
    num_strides_detected=None,
    cadence_avg=180.0,
    vertical_osc_avg_cm=8.0,
    knee_angle_strike_avg_deg=25.0,
    foot_strike_position_avg_cm=5.0,
    trunk_lean_avg_deg=5.0,
    strides=None,
):
    return {
        "meta": {"height_cm": 175},
        "summary": {
            "num_strides": num_strides,
            "num_strides_detected": num_strides_detected if num_strides_detected is not None else num_strides,
            "cadence_avg": cadence_avg,
            "vertical_osc_avg_cm": vertical_osc_avg_cm,
            "knee_angle_strike_avg_deg": knee_angle_strike_avg_deg,
            "foot_strike_position_avg_cm": foot_strike_position_avg_cm,
            "trunk_lean_avg_deg": trunk_lean_avg_deg,
        },
        "flags": [],
        "strides": strides if strides is not None else [{"stride_num": i} for i in range(num_strides)],
    }


# ---- Hard fail: the primary harm this whole feature exists to prevent ----
def test_hard_fail_on_too_few_strides_clears_summary_and_flags():
    """The exact real-world case: a 4-stride clip must produce no metrics
    and no coaching -- not a confidently-wrong number and a confidently-wrong
    drill. Emptying summary/flags is what routes the web report to the
    existing 'couldn't measure your gait' screen (see hasData in
    frontend/app/runs/[id]/page.tsx) and is what suppresses the dashboard
    PNG and PDF (see run_analysis / main.py's report.pdf endpoint)."""
    results = _results(num_strides=4, cadence_avg=91.4)
    gate, results = apply_confidence_gate(results)

    assert gate.hard_fail is True
    assert gate.reason == "insufficient_strides"
    assert results["summary"] == {}
    assert results["flags"] == []
    # Diagnostic data is kept, just not surfaced -- strides/meta let support
    # or an engineer see why the gate fired without re-processing the video.
    assert len(results["strides"]) == 4
    assert results["meta"]["confidence_gate"]["hard_fail"] is True
    assert results["meta"]["confidence_gate"]["usable_stride_count"] == 4


def test_hard_fail_on_implausible_cadence_even_with_enough_strides():
    """91.4 spm with plenty of strides -- the gate must still catch this;
    stride count alone isn't sufficient evidence of a trustworthy result."""
    results = _results(num_strides=20, cadence_avg=91.4)
    gate, results = apply_confidence_gate(results)

    assert gate.hard_fail is True
    assert gate.reason == "implausible_cadence"
    assert results["summary"] == {}
    assert results["flags"] == []


def test_hard_fail_produces_no_coaching_flags():
    """Explicit check that no coach tip / drill can survive a hard fail --
    evaluate_heuristics must never even run against gated-out data."""
    results = _results(num_strides=3, cadence_avg=91.4)
    gate, results = apply_confidence_gate(results)
    assert gate.hard_fail is True
    assert results["flags"] == []


# ---- Normal and low-confidence paths still coach normally ----
def test_normal_result_keeps_summary_and_computes_flags():
    results = _results(num_strides=20, cadence_avg=179.7)
    gate, results = apply_confidence_gate(results)

    assert gate.hard_fail is False
    assert gate.low_confidence is False
    assert results["summary"]["cadence_avg"] == 179.7
    assert results["meta"]["confidence_gate"]["hard_fail"] is False
    assert results["meta"]["confidence_gate"]["low_confidence"] is False


def test_low_confidence_result_still_reports_and_coaches():
    """9 strides: not a hard fail, but must be flagged low-confidence --
    metrics and coaching still come through (this is a caveat, not a
    suppression)."""
    results = _results(num_strides=9, cadence_avg=175.0)
    gate, results = apply_confidence_gate(results)

    assert gate.hard_fail is False
    assert gate.low_confidence is True
    assert results["summary"] != {}
    assert results["meta"]["confidence_gate"]["low_confidence"] is True
    assert results["meta"]["confidence_gate"]["usable_stride_count"] == 9
