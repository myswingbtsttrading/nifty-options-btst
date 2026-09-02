from pathlib import Path


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def test_main_contains_production_modes():
    source = _read("main.py")

    assert "--mode" in source
    assert '"3pm"' in source
    assert '"930"' in source
    assert '"915"' in source
    assert '"smoke"' in source


def test_main_contains_exit_audit_state():
    source = _read("main.py")

    assert "EXIT_FILE" in source
    assert "_save_exit_record" in source
    assert "last_btst_exit.json" in source


def test_3pm_workflow_exists():
    workflow = Path(".github/workflows/btst_3pm.yml")

    assert workflow.exists()

    source = workflow.read_text(encoding="utf-8")

    assert 'cron: "30 9 * * 1-5"' in source
    assert "python main.py --mode 3pm" in source
    assert "TELEGRAM_TOKEN" in source
    assert "TELEGRAM_CHAT_ID" in source
    assert "Persist BTST position state" in source


def test_930_workflow_exists():
    workflow = Path(".github/workflows/btst_915.yml")

    assert workflow.exists()

    source = workflow.read_text(encoding="utf-8")

    assert "NIFTY BTST 9:30 AM Exit" in source
    assert 'cron: "0 4 * * 1-5"' in source
    assert "python main.py --mode 930" in source
    assert "TELEGRAM_TOKEN" in source
    assert "TELEGRAM_CHAT_ID" in source
    assert "9:30 AM" in source


def test_930_workflow_persists_exit_record():
    source = _read(".github/workflows/btst_915.yml")

    assert "last_btst_exit.json" in source
    assert "Persist BTST exit state" in source
    assert "git push" in source


def test_workflows_use_python_312():
    workflow_3pm = _read(".github/workflows/btst_3pm.yml")
    workflow_930 = _read(".github/workflows/btst_915.yml")

    assert 'python-version: "3.12"' in workflow_3pm
    assert 'python-version: "3.12"' in workflow_930


def test_workflows_run_pytest_before_production():
    workflow_3pm = _read(".github/workflows/btst_3pm.yml")
    workflow_930 = _read(".github/workflows/btst_915.yml")

    assert "python -m pytest -q" in workflow_3pm
    assert "python -m pytest -q" in workflow_930


def test_notifier_requires_telegram_credentials():
    source = _read("notifier.py")

    assert "TELEGRAM_TOKEN" in source
    assert "TELEGRAM_CHAT_ID" in source
    assert "sendMessage" in source