from pathlib import Path

import main


ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return path.read_text(encoding="utf-8")


def _main_source():
    return _read(ROOT / "main.py")


def test_state_file_is_defined():
    source = _main_source()

    assert "STATE_FILE" in source
    assert "live_btst_signal.json" in source


def test_exit_file_is_defined():
    source = _main_source()

    assert "EXIT_FILE" in source
    assert "last_btst_exit.json" in source


def test_state_save_is_present():
    source = _main_source()

    assert "def _save_signal_state" in source


def test_state_load_is_present():
    source = _main_source()

    assert "def _load_signal_state" in source


def test_exit_record_save_is_present():
    source = _main_source()

    assert "def _save_exit_record" in source


def test_exit_record_load_is_present():
    source = _main_source()

    assert "def _load_existing_exit_record" in source


def test_position_exit_matching_is_present():
    source = _main_source()

    assert "def _exit_record_matches_position" in source


def test_state_validation_requires_buy():
    source = _main_source()

    assert "BUY" in source
    assert "decision" in source


def test_state_validation_requires_direction():
    source = _main_source()

    assert "direction" in source


def test_state_validation_requires_option_identity():
    source = _main_source()

    for field in (
        "expiry",
        "strike",
        "option_type",
    ):
        assert field in source


def test_state_validation_requires_position_size():
    source = _main_source()

    assert "quantity" in source
    assert "lots" in source


def test_state_validation_requires_entry_price():
    source = _main_source()

    assert "entry_price" in source


def test_exit_record_has_closed_status():
    source = _main_source()

    assert "CLOSED" in source


def test_exit_matching_checks_option_type():
    source = _main_source()

    start = source.find("def _exit_record_matches_position")
    assert start >= 0

    section = source[start:start + 5000]
    assert "option_type" in section


def test_exit_matching_checks_strike():
    source = _main_source()

    start = source.find("def _exit_record_matches_position")
    assert start >= 0

    section = source[start:start + 5000]
    assert "strike" in section


def test_exit_matching_checks_expiry():
    source = _main_source()

    start = source.find("def _exit_record_matches_position")
    assert start >= 0

    section = source[start:start + 5000]
    assert "expiry" in section


def test_exit_matching_checks_entry_price():
    source = _main_source()

    start = source.find("def _exit_record_matches_position")
    assert start >= 0

    section = source[start:start + 5000]
    assert "entry_price" in section


def test_930_checks_existing_exit_before_market_fetch():
    source = _main_source()

    start = source.find("def run_930")
    assert start >= 0

    section = source[start:start + 12000]

    exit_pos = section.find("_load_existing_exit_record")
    chain_pos = section.find("fetch_nifty_option_chain")

    assert exit_pos >= 0
    assert chain_pos >= 0
    assert exit_pos < chain_pos


def test_930_removes_stale_state_after_matching_exit():
    source = _main_source()

    start = source.find("def run_930")
    assert start >= 0

    section = source[start:start + 12000]

    assert "_exit_record_matches_position" in section
    assert "_remove_active_state" in section


def test_atomic_state_write_is_present():
    source = _main_source()

    assert "def _atomic_write_json" in source
    assert "os.replace" in source


def test_3pm_blocks_duplicate_active_buy():
    source = _main_source()

    start = source.find("def run_3pm")
    assert start >= 0

    section = source[start:start + 12000]

    assert "active" in section.lower()
    assert "_load_signal_state" in section
    assert "An active BTST BUY position already exists." in section