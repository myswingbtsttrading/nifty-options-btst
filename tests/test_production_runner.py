from pathlib import Path


def test_main_contains_production_modes():
    source = Path(
        "main.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "--mode" in source
    assert '"3pm"' in source
    assert '"930"' in source
    assert '"smoke"' in source


def test_3pm_workflow_exists():
    workflow = Path(
        ".github/workflows/btst_3pm.yml"
    )

    assert workflow.exists()

    source = workflow.read_text(
        encoding="utf-8"
    )

    assert 'cron: "30 9 * * 1-5"' in source
    assert "python main.py --mode 3pm" in source
    assert "TELEGRAM_TOKEN" in source
    assert "TELEGRAM_CHAT_ID" in source


def test_930_workflow_exists():
    workflow = Path(
        ".github/workflows/btst_915.yml"
    )

    assert workflow.exists()

    source = workflow.read_text(
        encoding="utf-8"
    )

    assert 'cron: "0 4 * * 1-5"' in source
    assert "python main.py --mode 930" in source
    assert "TELEGRAM_TOKEN" in source
    assert "TELEGRAM_CHAT_ID" in source
    assert "9:30 AM" in source


def test_notifier_requires_telegram_credentials():
    source = Path(
        "notifier.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "TELEGRAM_TOKEN" in source
    assert "TELEGRAM_CHAT_ID" in source
    assert "sendMessage" in source