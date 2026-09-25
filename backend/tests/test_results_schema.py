"""Tests for the results JSON schema (backend/schema/results.schema.json) and the
read-time rear-view merge (backend/results_schema.py). The point of the schema
versioning: single-view runs written before the rear view existed must stay
valid untouched."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

jsonschema = pytest.importorskip("jsonschema")

from backend import results_schema as rs  # noqa: E402
from backend.rear_metrics import compute_rear_metrics  # noqa: E402
from backend.tests.rear_fixtures import CYCLE_FRAMES, FPS, make_rear_frames  # noqa: E402

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"
SCHEMA = json.loads((SCHEMA_DIR / "results.schema.json").read_text())
SAMPLE = json.loads((SCHEMA_DIR / "sample_run_both_views.json").read_text())
validator = jsonschema.Draft202012Validator(SCHEMA)


def _errors(doc):
    return [e.message for e in validator.iter_errors(doc)]


def _legacy_v1():
    """A results document exactly as the side pipeline wrote it before schema
    versioning: no schema_version, no rear_view."""
    doc = copy.deepcopy(SAMPLE)
    del doc["schema_version"], doc["rear_view"]
    return doc


def test_schema_itself_is_valid():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


def test_sample_with_both_views_validates():
    assert _errors(SAMPLE) == []
    assert SAMPLE["schema_version"] == 2 and SAMPLE["rear_view"]["status"] == "ok"


def test_legacy_single_view_documents_stay_valid_with_no_migration():
    legacy = _legacy_v1()
    assert "schema_version" not in legacy
    assert _errors(legacy) == []
    assert rs.schema_version_of(legacy) == 1
    # A side-only doc that has been stamped v2 (no rear_view) is valid too.
    assert _errors({**legacy, "schema_version": 2}) == []


def test_hard_failed_side_run_still_validates():
    """Side confidence-gate hard fail: summary/flags emptied — must stay valid."""
    doc = _legacy_v1()
    doc["summary"], doc["flags"] = {}, []
    assert _errors(doc) == []


def test_rear_view_requires_schema_version_2():
    doc = _legacy_v1()
    doc["rear_view"] = SAMPLE["rear_view"]
    assert _errors(doc)
    assert _errors({**doc, "schema_version": 1})
    assert _errors({**doc, "schema_version": 2}) == []


@pytest.mark.parametrize("placeholder", [{"status": "processing"}, {"status": "failed", "error": "rear_analysis_failed"}])
def test_pending_and_failed_placeholders_validate(placeholder):
    doc = {**_legacy_v1(), "schema_version": 2, "rear_view": placeholder}
    assert _errors(doc) == []


def test_bad_rear_view_is_rejected():
    for mutate in (
        lambda rv: rv["legs"]["left"]["knee_valgus"].update(pattern="made_up"),
        lambda rv: rv["legs"]["left"]["experimental"]["hip_drop"].pop("disclaimer"),
        lambda rv: rv["meta"].update(synchronized_with_side_view=True),
        lambda rv: rv["curves"]["left"]["hip_drop_deg"].pop(),
        lambda rv: rv["symmetry"].update(score=140),
    ):
        doc = copy.deepcopy(SAMPLE)
        mutate(doc["rear_view"])
        assert _errors(doc), mutate


@pytest.mark.parametrize("n_frames", [360, CYCLE_FRAMES * 7 + 5, int(FPS * 1.5) + 21, 60])
def test_every_kind_of_real_compute_output_validates(n_frames):
    """ok, low_confidence and insufficient_data outputs of the real module."""
    rv = compute_rear_metrics(make_rear_frames(n_frames=n_frames), FPS, video_file="rear.mp4")
    assert _errors(rs.attach_rear_view(_legacy_v1(), rv)) == []


def test_empty_rear_view_validates():
    rv = compute_rear_metrics([], FPS)
    assert _errors(rs.attach_rear_view(_legacy_v1(), rv)) == []


# ---- read-time merge ---------------------------------------------------------------------
def test_attach_rear_view_does_not_mutate_the_stored_side_results():
    legacy = _legacy_v1()
    before = copy.deepcopy(legacy)
    merged = rs.attach_rear_view(legacy, SAMPLE["rear_view"])
    assert legacy == before
    assert merged["schema_version"] == 2 and merged["rear_view"] == SAMPLE["rear_view"]
    assert merged["summary"] == legacy["summary"]


def test_attach_rear_view_is_a_no_op_without_a_rear_view_or_side_results():
    legacy = _legacy_v1()
    assert rs.attach_rear_view(legacy, None) is legacy
    assert rs.attach_rear_view(None, SAMPLE["rear_view"]) is None
    assert rs.attach_rear_view({}, SAMPLE["rear_view"]) == {}


def test_rear_view_from_video_row_maps_pipeline_state():
    assert rs.rear_view_from_video_row(None) is None
    assert rs.rear_view_from_video_row(SimpleNamespace(status="processing", results_json=None, error_message=None)) == {"status": "processing"}
    done = SimpleNamespace(status="complete", results_json=SAMPLE["rear_view"], error_message=None)
    assert rs.rear_view_from_video_row(done) == SAMPLE["rear_view"]


def test_failed_rear_view_never_leaks_the_internal_error_text():
    row = SimpleNamespace(status="failed", results_json=None, error_message="psycopg2.OperationalError: host=10.0.0.5 ...")
    rv = rs.rear_view_from_video_row(row)
    assert rv == {"status": "failed", "error": "rear_analysis_failed"}
    assert "psycopg2" not in json.dumps(rv)


def test_rear_results_stored_before_hip_drop_went_experimental_still_validate():
    """metrics_version 2 rows (already in the DB) carry hip_drop at the top of
    each leg and include it in symmetry; they must stay valid with no migration."""
    doc = copy.deepcopy(SAMPLE)
    rv = doc["rear_view"]
    rv["meta"]["metrics_version"] = 2
    for leg in ("left", "right"):
        rv["legs"][leg]["hip_drop"] = rv["legs"][leg]["experimental"].pop("hip_drop")
    rv["symmetry"]["components"]["hip_drop"] = 90
    assert _errors(doc) == []
