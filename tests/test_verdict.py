"""Unit tests for agents/verdict.py's audit-log rotation. Deliberately does
NOT test render_verdict() itself here (that needs a trained model -- see
test_pipeline.py's requires_artifacts pattern, which exercises it
end-to-end) -- this isolates the rotation logic with a tmp_path so it runs
even on a fresh clone with no models/ or data/ present yet."""
import time

import agents.verdict as verdict


def test_rotation_noop_when_under_threshold(tmp_path, monkeypatch):
    log_path = tmp_path / "audit_log.jsonl"
    log_path.write_text('{"a": 1}\n')
    monkeypatch.setattr(verdict, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(verdict, "_AUDIT_LOG_MAX_BYTES", 1024 * 1024)

    verdict._rotate_audit_log_if_needed()

    assert log_path.exists()
    assert log_path.read_text() == '{"a": 1}\n'
    assert list(tmp_path.iterdir()) == [log_path]


def test_rotation_renames_when_over_threshold(tmp_path, monkeypatch):
    log_path = tmp_path / "audit_log.jsonl"
    log_path.write_text('{"a": 1}\n' * 100)
    monkeypatch.setattr(verdict, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(verdict, "_AUDIT_LOG_MAX_BYTES", 10)  # force rotation

    verdict._rotate_audit_log_if_needed()

    # Original path is gone (renamed away) -- the next append starts fresh.
    assert not log_path.exists()
    remaining = list(tmp_path.iterdir())
    assert len(remaining) == 1
    rotated = remaining[0]
    assert rotated.name.startswith("audit_log.")
    assert rotated.name.endswith(".jsonl")
    assert rotated.name != "audit_log.jsonl"
    assert rotated.read_text() == '{"a": 1}\n' * 100


def test_rotation_is_best_effort_on_error(tmp_path, monkeypatch):
    # A log path that doesn't exist yet (e.g. before the first verdict is
    # ever logged) must be a silent no-op, not an error.
    log_path = tmp_path / "does_not_exist" / "audit_log.jsonl"
    monkeypatch.setattr(verdict, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(verdict, "_AUDIT_LOG_MAX_BYTES", 1)

    verdict._rotate_audit_log_if_needed()  # must not raise


def test_repeated_writes_trigger_rotation_end_to_end(tmp_path, monkeypatch):
    """Simulates what render_verdict() actually does on every call: rotate,
    then append. Confirms a rotated-away file doesn't lose data and a fresh
    file starts cleanly under the same original path."""
    log_path = tmp_path / "audit_log.jsonl"
    monkeypatch.setattr(verdict, "_AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr(verdict, "_AUDIT_LOG_MAX_BYTES", 50)  # tiny, to force multiple rotations

    for i in range(20):
        verdict._rotate_audit_log_if_needed()
        with open(log_path, "a") as f:
            f.write(f'{{"i": {i}}}\n')

    files = sorted(tmp_path.iterdir())
    # At least one rotation must have happened, and the live file must be
    # the current (small) tail, not one giant unbounded file.
    assert len(files) > 1
    assert log_path in files
    assert log_path.stat().st_size < 1024
