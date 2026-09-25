import logging

from backend.step_timer import StepTimer


def test_steps_accumulate_and_summary_lists_them_in_order():
    t = StepTimer()
    t.add("pose", 1.0)
    t.add("decode", 0.25)
    t.add("pose", 2.0)
    t.info.update(source_fps=59.94, frames_used=300, truncated=True)
    summary = t.summary()
    assert summary.startswith("total=")
    assert "pose=3.0s decode=0.2s" in summary
    assert "source_fps=59.94 frames_used=300 truncated=True" in summary


def test_step_records_time_even_when_the_block_raises():
    t = StepTimer()
    try:
        with t.step("encode"):
            raise RuntimeError("ffmpeg failed")
    except RuntimeError:
        pass
    assert "encode" in t.steps


def test_log_line_is_greppable(caplog):
    t = StepTimer()
    t.add("pose", 1.0)
    with caplog.at_level(logging.INFO):
        t.log(logging.getLogger("test"), "rear", "abc", "complete")
    assert "pipeline_timing view=rear run_id=abc status=complete total=" in caplog.text
    assert "pose=1.0s" in caplog.text
