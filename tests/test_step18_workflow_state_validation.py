from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_workflow(name):
    return (
        ROOT
        / ".github"
        / "workflows"
        / name
    ).read_text(encoding="utf-8")


def test_3pm_workflow_validates_active_state():
    workflow = _read_workflow("btst_3pm.yml")

    assert "Validate active BTST state" in workflow
    assert "live_btst_signal.json" in workflow
    assert '"decision"' in workflow
    assert '"direction"' in workflow
    assert '"expiry"' in workflow
    assert '"strike"' in workflow
    assert '"option_type"' in workflow
    assert '"entry_price"' in workflow
    assert '"quantity"' in workflow
    assert '"lots"' in workflow
    assert 'payload["decision"] != "BUY"' in workflow
    assert 'payload["option_type"] not in {"CE", "PE"}' in workflow


def test_930_workflow_validates_exit_record():
    workflow = _read_workflow("btst_915.yml")

    assert "Validate exit record" in workflow
    assert "last_btst_exit.json" in workflow
    assert '"status"' in workflow
    assert '"closed_at"' in workflow
    assert '"entry_timestamp"' in workflow
    assert '"exit_timestamp"' in workflow
    assert '"direction"' in workflow
    assert '"option_type"' in workflow
    assert '"strike"' in workflow
    assert '"expiry"' in workflow
    assert '"entry_price"' in workflow
    assert '"exit_price"' in workflow
    assert '"quantity"' in workflow
    assert '"lots"' in workflow
    assert '"pnl"' in workflow
    assert '"pnl_pct"' in workflow
    assert 'payload["status"] != "CLOSED"' in workflow


def test_3pm_runs_tests_before_live_signal():
    workflow = _read_workflow("btst_3pm.yml")

    assert workflow.index(
        "Run test suite"
    ) < workflow.index(
        "Generate 3 PM BTST signal"
    )


def test_930_runs_tests_before_live_exit():
    workflow = _read_workflow("btst_915.yml")

    assert workflow.index(
        "Run test suite"
    ) < workflow.index(
        "Generate 9:30 AM SELL alert"
    )


def test_3pm_persists_state_after_validation():
    workflow = _read_workflow("btst_3pm.yml")

    assert workflow.index(
        "Validate active BTST state"
    ) < workflow.index(
        "Persist BTST position state"
    )


def test_930_persists_exit_after_validation():
    workflow = _read_workflow("btst_915.yml")

    assert workflow.index(
        "Validate exit record"
    ) < workflow.index(
        "Remove closed BTST position state"
    )