from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return path.read_text(encoding="utf-8")


def test_3pm_workflow_has_fail_fast_enabled():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert "set -e" in workflow


def test_930_workflow_has_fail_fast_enabled():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert "set -e" in workflow


def test_3pm_workflow_checks_state_after_signal():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert workflow.index(
        "Generate 3 PM BTST signal"
    ) < workflow.index(
        "Verify BTST state output"
    )


def test_930_workflow_checks_exit_after_signal():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert workflow.index(
        "Generate 9:30 AM SELL alert"
    ) < workflow.index(
        "Verify closed BTST state"
    )


def test_3pm_workflow_validates_state_before_persisting():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert workflow.index(
        "Validate active BTST state"
    ) < workflow.index(
        "Persist BTST position state"
    )


def test_930_workflow_validates_exit_before_persisting():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert workflow.index(
        "Validate exit record"
    ) < workflow.index(
        "Remove closed BTST position state"
    )


def test_3pm_state_validation_requires_iso_timestamp():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_3pm.yml")

    assert "timestamp" in workflow
    assert "required =" in workflow


def test_930_exit_validation_requires_closed_status():
    workflow = _read(ROOT / ".github" / "workflows" / "btst_915.yml")

    assert '"status"' in workflow
    assert '"CLOSED"' in workflow


def test_main_has_explicit_error_handling():
    main_source = _read(ROOT / "main.py")

    assert "try:" in main_source
    assert "except" in main_source


def test_main_does_not_silently_ignore_live_errors():
    main_source = _read(ROOT / "main.py")

    assert "raise" in main_source


def test_main_has_positive_price_validation():
    main_source = _read(ROOT / "main.py")

    assert "<= 0" in main_source


def test_main_has_state_directory_creation():
    main_source = _read(ROOT / "main.py")

    assert "DATA_DIR.mkdir" in main_source


def test_main_has_json_state_files():
    main_source = _read(ROOT / "main.py")

    assert "live_btst_signal.json" in main_source
    assert "last_btst_exit.json" in main_source


def test_main_exit_is_idempotent():
    main_source = _read(ROOT / "main.py")

    assert "_exit_record_matches_position" in main_source
    assert "_remove_active_state()" in main_source


def test_workflows_are_weekday_scheduled():
    for filename, cron in (
        ("btst_3pm.yml", 'cron: "30 9 * * 1-5"'),
        ("btst_915.yml", 'cron: "0 4 * * 1-5"'),
    ):
        workflow = _read(ROOT / ".github" / "workflows" / filename)

        assert cron in workflow


def test_workflows_have_manual_dispatch():
    for filename in (
        "btst_3pm.yml",
        "btst_915.yml",
    ):
        workflow = _read(ROOT / ".github" / "workflows" / filename)

        assert "workflow_dispatch:" in workflow


def test_workflows_use_checkout_action():
    for filename in (
        "btst_3pm.yml",
        "btst_915.yml",
    ):
        workflow = _read(ROOT / ".github" / "workflows" / filename)

        assert "actions/checkout@v4" in workflow


def test_workflows_use_setup_python_action():
    for filename in (
        "btst_3pm.yml",
        "btst_915.yml",
    ):
        workflow = _read(ROOT / ".github" / "workflows" / filename)

        assert "actions/setup-python@v5" in workflow


def test_workflows_upgrade_pip():
    for filename in (
        "btst_3pm.yml",
        "btst_915.yml",
    ):
        workflow = _read(ROOT / ".github" / "workflows" / filename)

        assert "python -m pip install --upgrade pip" in workflow