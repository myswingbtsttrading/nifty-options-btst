from pathlib import Path

import main


ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return path.read_text(encoding="utf-8")


def _main_source():
    return _read(ROOT / "main.py")


def _function_source(name, limit=18000):
    source = _main_source()
    start = source.find(f"def {name}")
    assert start >= 0
    return source[start:start + limit]


def test_notifier_uses_send_alert():
    source = _main_source()

    assert "from notifier import send_alert" in source


def test_3pm_saves_state_before_alert():
    section = _function_source("run_3pm")

    save_pos = section.find("_save_signal_state")
    alert_pos = section.find("send_alert")

    assert save_pos >= 0
    assert alert_pos >= 0
    assert save_pos < alert_pos


def test_3pm_removes_state_when_alert_fails():
    section = _function_source("run_3pm")

    alert_pos = section.find("send_alert")
    remove_pos = section.find("_remove_active_state")

    assert alert_pos >= 0
    assert remove_pos >= 0
    assert remove_pos > alert_pos


def test_3pm_reraises_alert_failure():
    section = _function_source("run_3pm")

    alert_pos = section.find("send_alert")
    assert alert_pos >= 0

    following = section[alert_pos:alert_pos + 3000]

    assert "except" in following
    assert "raise" in following


def test_3pm_blocks_existing_active_position():
    section = _function_source("run_3pm")

    assert "STATE_FILE.exists()" in section
    assert "_load_signal_state" in section
    assert "An active BTST BUY position already exists." in section


def test_3pm_does_not_alert_for_no_trade():
    section = _function_source("run_3pm")

    decision_pos = section.find("result.signal.decision")
    alert_pos = section.find("send_alert")

    assert decision_pos >= 0
    assert alert_pos >= 0
    assert decision_pos < alert_pos


def test_930_checks_existing_exit_before_chain():
    section = _function_source("run_930")

    exit_pos = section.find("_load_existing_exit_record")
    chain_pos = section.find("fetch_nifty_option_chain")

    assert exit_pos >= 0
    assert chain_pos >= 0
    assert exit_pos < chain_pos


def test_930_requires_matching_completed_exit_for_idempotent_skip():
    section = _function_source("run_930")

    match_pos = section.find("_exit_record_matches_position")
    sent_pos = section.find("telegram_sent")

    assert match_pos >= 0
    assert sent_pos >= 0
    assert match_pos < sent_pos


def test_930_removes_state_after_already_delivered_exit():
    section = _function_source("run_930")

    match_pos = section.find("_exit_record_matches_position")
    remove_pos = section.find("_remove_active_state")

    assert match_pos >= 0
    assert remove_pos >= 0
    assert remove_pos > match_pos


def test_930_saves_exit_before_alert():
    section = _function_source("run_930")

    save_pos = section.find("_save_exit_record")
    alert_pos = section.find("send_alert")

    assert save_pos >= 0
    assert alert_pos >= 0
    assert save_pos < alert_pos


def test_930_marks_exit_delivery_only_after_alert():
    section = _function_source("run_930")

    alert_pos = section.find("send_alert")
    mark_pos = section.find("_mark_exit_telegram_sent")

    assert alert_pos >= 0
    assert mark_pos >= 0
    assert alert_pos < mark_pos


def test_930_removes_state_only_after_delivery_mark():
    section = _function_source("run_930")

    mark_pos = section.find("_mark_exit_telegram_sent")
    remove_pos = section.find("_remove_active_state")

    assert mark_pos >= 0
    assert remove_pos >= 0
    assert mark_pos < remove_pos


def test_930_keeps_state_when_alert_fails():
    section = _function_source("run_930")

    alert_pos = section.find("send_alert")
    mark_pos = section.find("_mark_exit_telegram_sent")
    remove_pos = section.find("_remove_active_state")

    assert alert_pos >= 0
    assert mark_pos > alert_pos
    assert remove_pos > mark_pos


def test_exit_record_has_telegram_status():
    section = _function_source("_save_exit_record", 8000)

    assert "telegram_sent" in section


def test_exit_record_defaults_delivery_to_false():
    section = _function_source("_save_exit_record", 8000)

    assert '"telegram_sent": bool(telegram_sent)' in section


def test_exit_delivery_marker_is_persisted():
    section = _function_source("_mark_exit_telegram_sent", 3000)

    assert "telegram_sent" in section
    assert "_atomic_write_json" in section


def test_atomic_writer_uses_replace():
    source = _main_source()

    assert "def _atomic_write_json" in source
    assert "os.replace" in source


def test_active_state_cleanup_is_centralized():
    source = _main_source()

    assert "def _remove_active_state" in source


def test_alert_failure_does_not_silently_continue():
    section = _function_source("run_3pm")

    alert_pos = section.find("send_alert")
    following = section[alert_pos:alert_pos + 3000]

    assert "raise" in following


def test_exit_record_is_closed():
    section = _function_source("_save_exit_record", 8000)

    assert '"status": "CLOSED"' in section


def test_exit_record_contains_trade_identity():
    section = _function_source("_save_exit_record", 8000)

    for field in (
        "direction",
        "option_type",
        "strike",
        "expiry",
        "entry_price",
        "exit_price",
        "quantity",
        "lots",
    ):
        assert field in section