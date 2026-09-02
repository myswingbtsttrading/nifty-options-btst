from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return path.read_text(encoding="utf-8")


def test_3pm_workflow_has_concurrency_control():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert "concurrency:" in workflow


def test_930_workflow_has_concurrency_control():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert "concurrency:" in workflow


def test_3pm_concurrency_prevents_overlapping_runs():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert "cancel-in-progress: false" in workflow


def test_930_concurrency_prevents_overlapping_runs():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert "cancel-in-progress: false" in workflow


def test_3pm_workflow_has_timeout():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert "timeout-minutes:" in workflow


def test_930_workflow_has_timeout():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert "timeout-minutes:" in workflow


def test_3pm_workflow_has_write_permission():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert "contents: write" in workflow


def test_930_workflow_has_write_permission():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert "contents: write" in workflow


def test_3pm_signal_runs_only_after_tests_pass():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert workflow.index("Run test suite") < workflow.index(
        "Generate 3 PM BTST signal"
    )


def test_930_exit_runs_only_after_tests_pass():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert workflow.index("Run test suite") < workflow.index(
        "Generate 9:30 AM SELL alert"
    )


def test_3pm_state_persistence_is_after_signal_generation():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert workflow.index(
        "Generate 3 PM BTST signal"
    ) < workflow.index(
        "Persist BTST position state"
    )


def test_930_state_persistence_is_after_exit_generation():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert workflow.index(
        "Generate 9:30 AM SELL alert"
    ) < workflow.index(
        "Remove closed BTST position state"
    )


def test_3pm_workflow_has_manual_trigger():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert "workflow_dispatch:" in workflow


def test_930_workflow_has_manual_trigger():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert "workflow_dispatch:" in workflow


def test_3pm_workflow_uses_python_312():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert 'python-version: "3.12"' in workflow


def test_930_workflow_uses_python_312():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert 'python-version: "3.12"' in workflow


def test_3pm_workflow_persists_only_state_file():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert 'git add -- "$STATE_FILE"' in workflow


def test_930_workflow_persists_exit_file():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert 'git add -- "$EXIT_FILE"' in workflow


def test_3pm_workflow_pushes_state_changes():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert "git push" in workflow


def test_930_workflow_pushes_exit_changes():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert "git push" in workflow