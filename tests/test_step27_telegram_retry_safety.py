from pathlib import Path


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


def _remove_after_alert(section):
    alert_pos = section.find("send_alert")
    assert alert_pos >= 0

    remove_pos = section.find(
        "_remove_active_state",
        alert_pos,
    )

    assert remove_pos >= 0
    return alert_pos, remove_pos


def test_notifier_uses_send_alert():
    source = _main_source()

    assert "from notifier import send_alert" in source


def test_3pm_checks_duplicate_before_formatting():
    section = _function_source("run_3pm")

    duplicate_pos = section.find(
        "An active BTST BUY position already exists."
    )
    format_pos = section.find(
        "_format_signal_message"
    )

    assert duplicate_pos >= 0
    assert format_pos >= 0
    assert duplicate_pos < format_pos


def test_3pm_saves_state_before_alert():
    section = _function_source("run_3pm")

    save_pos = section.find(
        "_save_signal_state"
    )
    alert_pos = section.find(
        "send_alert"
    )

    assert save_pos >= 0
    assert alert_pos >= 0
    assert save_pos < alert_pos


def test_3pm_removes_state_when_alert_fails():
    section = _function_source("run_3pm")

    alert_pos = section.find(
        "send_alert"
    )
    remove_pos = section.find(
        "_remove_active_state",
        alert_pos,
    )

    assert alert_pos >= 0
    assert remove_pos >= 0
    assert remove_pos > alert_pos


def test_3pm_reraises_alert_failure():
    section = _function_source("run_3pm")

    alert_pos = section.find(
        "send_alert"
    )

    assert alert_pos >= 0

    following = section[
        alert_pos:alert_pos + 3000
    ]

    assert "except" in following
    assert "raise" in following


def test_930_checks_completed_exit_before_chain():
    section = _function_source("run_930")

    exit_pos = section.find(
        "_load_existing_exit_record"
    )
    match_pos = section.find(
        "_exit_record_matches_position"
    )
    chain_pos = section.find(
        "fetch_nifty_option_chain"
    )

    assert exit_pos >= 0
    assert match_pos >= 0
    assert chain_pos >= 0

    assert exit_pos < chain_pos
    assert match_pos < chain_pos


def test_930_matching_exit_removes_state():
    section = _function_source("run_930")

    match_pos = section.find(
        "_exit_record_matches_position"
    )
    remove_pos = section.find(
        "_remove_active_state",
        match_pos,
    )

    assert match_pos >= 0
    assert remove_pos >= 0
    assert match_pos < remove_pos


def test_930_matching_exit_does_not_alert():
    section = _function_source("run_930")

    match_pos = section.find(
        "_exit_record_matches_position"
    )
    alert_pos = section.find(
        "send_alert"
    )

    assert match_pos >= 0
    assert alert_pos >= 0
    assert match_pos < alert_pos


def test_930_saves_exit_before_alert():
    section = _function_source("run_930")

    save_pos = section.find(
        "_save_exit_record"
    )
    alert_pos = section.find(
        "send_alert"
    )

    assert save_pos >= 0
    assert alert_pos >= 0
    assert save_pos < alert_pos


def test_930_keeps_state_when_alert_fails():
    section = _function_source("run_930")

    alert_pos, remove_pos = _remove_after_alert(
        section
    )

    assert alert_pos < remove_pos


def test_930_removes_state_after_successful_alert():
    section = _function_source("run_930")

    alert_pos, remove_pos = _remove_after_alert(
        section
    )

    assert alert_pos < remove_pos


def test_exit_record_is_closed():
    section = _function_source(
        "_save_exit_record",
        8000,
    )

    assert '"status": "CLOSED"' in section


def test_exit_record_contains_trade_identity():
    section = _function_source(
        "_save_exit_record",
        8000,
    )

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


def test_exit_record_contains_pnl():
    section = _function_source(
        "_save_exit_record",
        8000,
    )

    assert "pnl" in section
    assert "pnl_pct" in section


def test_exit_record_uses_atomic_writer():
    section = _function_source(
        "_save_exit_record",
        8000,
    )

    assert "_atomic_write_json" in section


def test_atomic_writer_uses_replace():
    source = _main_source()

    assert "def _atomic_write_json" in source
    assert "os.replace" in source


def test_active_state_cleanup_is_defined():
    source = _main_source()

    assert "def _remove_active_state" in source


def test_telegram_failure_is_reraised():
    section = _function_source("run_930")

    alert_pos = section.find(
        "send_alert"
    )

    assert alert_pos >= 0

    following = section[
        alert_pos:alert_pos + 3000
    ]

    assert "except" in following
    assert "raise" in following


def test_3pm_only_alerts_for_buy():
    section = _function_source("run_3pm")

    decision_pos = section.find(
        "result.signal.decision"
    )
    alert_pos = section.find(
        "send_alert"
    )

    assert decision_pos >= 0
    assert alert_pos >= 0
    assert decision_pos < alert_pos


def test_930_uses_exact_stored_contract():
    section = _function_source("run_930")

    assert 'position["expiry"]' in section
    assert 'position["option_type"]' in section
    assert 'position["strike"]' in section


def test_exit_record_matching_is_explicit():
    source = _main_source()

    start = source.find(
        "def _exit_record_matches_position"
    )

    assert start >= 0

    section = source[
        start:start + 7000
    ]

    for field in (
        "direction",
        "option_type",
        "expiry",
        "strike",
        "entry_price",
        "quantity",
        "lots",
    ):
        assert field in section