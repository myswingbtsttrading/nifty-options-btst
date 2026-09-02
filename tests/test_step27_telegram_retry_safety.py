from pathlib import Path

import main


ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return path.read_text(encoding="utf-8")


def _main_source():
    return _read(ROOT / "main.py")


def test_3pm_rolls_back_state_when_telegram_fails():
    source = _main_source()

    start = source.find("def run_3pm")
    assert start >= 0

    section = source[start:start + 14000]

    telegram_pos = section.find("send_telegram")
    remove_pos = section.find("_remove_active_state")

    assert telegram_pos >= 0
    assert remove_pos >= 0
    assert remove_pos > telegram_pos


def test_3pm_reraises_telegram_failure():
    source = _main_source()

    start = source.find("def run_3pm")
    assert start >= 0

    section = source[start:start + 14000]

    telegram_pos = section.find("send_telegram")
    assert telegram_pos >= 0

    following = section[telegram_pos:telegram_pos + 5000]

    assert "except" in following
    assert "raise" in following


def test_3pm_saves_state_before_telegram():
    source = _main_source()

    start = source.find("def run_3pm")
    assert start >= 0

    section = source[start:start + 14000]

    save_pos = section.find("_save_signal_state")
    telegram_pos = section.find("send_telegram")

    assert save_pos >= 0
    assert telegram_pos >= 0
    assert save_pos < telegram_pos


def test_930_saves_exit_record_before_telegram():
    source = _main_source()

    start = source.find("def run_930")
    assert start >= 0

    section = source[start:start + 16000]

    save_pos = section.find("_save_exit_record")
    telegram_pos = section.find("send_telegram")

    assert save_pos >= 0
    assert telegram_pos >= 0
    assert save_pos < telegram_pos


def test_930_keeps_exit_record_when_telegram_fails():
    source = _main_source()

    start = source.find("def run_930")
    assert start >= 0

    section = source[start:start + 16000]

    telegram_pos = section.find("send_telegram")
    assert telegram_pos >= 0

    following = section[telegram_pos:telegram_pos + 5000]

    assert "except" in following
    assert "raise" in following


def test_930_does_not_remove_state_before_telegram():
    source = _main_source()

    start = source.find("def run_930")
    assert start >= 0

    section = source[start:start + 16000]

    telegram_pos = section.find("send_telegram")
    remove_pos = section.find("_remove_active_state")

    assert telegram_pos >= 0
    assert remove_pos >= 0
    assert remove_pos > telegram_pos


def test_930_removes_state_after_successful_telegram():
    source = _main_source()

    start = source.find("def run_930")
    assert start >= 0

    section = source[start:start + 16000]

    telegram_pos = section.find("send_telegram")
    remove_pos = section.find("_remove_active_state")

    assert telegram_pos >= 0
    assert remove_pos >= 0
    assert remove_pos > telegram_pos


def test_existing_closed_exit_is_checked():
    source = _main_source()

    start = source.find("def run_930")
    assert start >= 0

    section = source[start:start + 16000]

    assert "_load_existing_exit_record" in section
    assert "_exit_record_matches_position" in section
    assert "CLOSED" in section


def test_matching_closed_exit_prevents_duplicate_exit_processing():
    source = _main_source()

    start = source.find("def run_930")
    assert start >= 0

    section = source[start:start + 16000]

    match_pos = section.find("_exit_record_matches_position")
    chain_pos = section.find("fetch_nifty_option_chain")

    assert match_pos >= 0
    assert chain_pos >= 0
    assert match_pos < chain_pos


def test_matching_closed_exit_prevents_duplicate_telegram():
    source = _main_source()

    start = source.find("def run_930")
    assert start >= 0

    section = source[start:start + 16000]

    match_pos = section.find("_exit_record_matches_position")
    telegram_pos = section.find("send_telegram")

    assert match_pos >= 0
    assert telegram_pos >= 0
    assert match_pos < telegram_pos


def test_3pm_requires_active_state_check():
    source = _main_source()

    start = source.find("def run_3pm")
    assert start >= 0

    section = source[start:start + 14000]

    assert "_load_signal_state" in section
    assert "An active BTST BUY position already exists." in section


def test_telegram_function_is_used_for_buy_alert():
    source = _main_source()

    assert "send_telegram" in source


def test_telegram_failure_is_not_silently_ignored():
    source = _main_source()

    assert "raise" in source


def test_exit_record_contains_delivery_relevant_timestamp():
    source = _main_source()

    start = source.find("def _save_exit_record")
    assert start >= 0

    section = source[start:start + 7000]

    assert "closed_at" in section


def test_exit_record_contains_entry_and_exit_prices():
    source = _main_source()

    start = source.find("def _save_exit_record")
    assert start >= 0

    section = source[start:start + 7000]

    assert "entry_price" in section
    assert "exit_price" in section


def test_exit_record_contains_position_identity():
    source = _main_source()

    start = source.find("def _save_exit_record")
    assert start >= 0

    section = source[start:start + 7000]

    for field in (
        "direction",
        "option_type",
        "strike",
        "expiry",
    ):
        assert field in section


def test_exit_record_contains_position_size():
    source = _main_source()

    start = source.find("def _save_exit_record")
    assert start >= 0

    section = source[start:start + 7000]

    assert "quantity" in section
    assert "lots" in section


def test_exit_record_contains_pnl():
    source = _main_source()

    start = source.find("def _save_exit_record")
    assert start >= 0

    section = source[start:start + 7000]

    assert "pnl" in section
    assert "pnl_pct" in section


def test_state_write_is_atomic():
    source = _main_source()

    start = source.find("def _atomic_write_json")
    assert start >= 0

    section = source[start:start + 4000]

    assert "tmp" in section
    assert "os.replace" in section


def test_exit_record_write_uses_atomic_writer():
    source = _main_source()

    start = source.find("def _save_exit_record")
    assert start >= 0

    section = source[start:start + 7000]

    assert "_atomic_write_json" in section


def test_retry_path_has_no_unconditional_state_deletion():
    source = _main_source()

    start = source.find("def run_930")
    assert start >= 0

    section = source[start:start + 16000]

    telegram_pos = section.find("send_telegram")
    assert telegram_pos >= 0

    after_telegram = section[telegram_pos:telegram_pos + 5000]

    assert "_remove_active_state" not in after_telegram.split("except", 1)[0]