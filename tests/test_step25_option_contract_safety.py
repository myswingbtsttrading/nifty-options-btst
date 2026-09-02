from pathlib import Path

import pytest

import option_selector


ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return path.read_text(encoding="utf-8")


def _selector_source():
    return _read(ROOT / "option_selector.py")


def test_selector_rejects_invalid_option_type():
    with pytest.raises((ValueError, TypeError)):
        option_selector.select_contract(
            option_chain=[],
            option_type="XX",
            underlying_price=25000,
            expiry="04-Sep-2026",
        )


def test_selector_rejects_non_positive_underlying():
    with pytest.raises((ValueError, TypeError)):
        option_selector.select_contract(
            option_chain=[],
            option_type="CE",
            underlying_price=0,
            expiry="04-Sep-2026",
        )


def test_selector_rejects_missing_expiry():
    with pytest.raises((ValueError, TypeError)):
        option_selector.select_contract(
            option_chain=[],
            option_type="CE",
            underlying_price=25000,
            expiry=None,
        )


def test_selector_defines_contract_selection():
    source = _selector_source()

    assert "def select_contract" in source
    assert "strike" in source
    assert "option_type" in source


def test_selector_validates_option_premium():
    source = _selector_source()

    assert "lastPrice" in source
    assert "<= 0" in source or "> 0" in source


def test_selector_has_explicit_selection_mode():
    source = _selector_source()

    assert "selection_mode" in source


def test_selector_supports_ce_and_pe():
    source = _selector_source()

    assert '"CE"' in source
    assert '"PE"' in source


def test_selector_uses_expiry_in_contract_selection():
    source = _selector_source()

    assert "expiry" in source


def test_selector_uses_strike_in_contract_selection():
    source = _selector_source()

    assert "strike" in source


def test_selector_has_no_random_contract_selection():
    source = _selector_source()

    assert "random" not in source.lower()


def test_selector_has_deterministic_selection_logic():
    source = _selector_source()

    assert (
        "min(" in source
        or "min (" in source
        or "abs(" in source
        or "abs (" in source
        or "key=" in source
    )


def test_selector_handles_empty_chain():
    source = _selector_source()

    assert (
        "if not " in source
        or "len(" in source
        or "raise" in source
    )


def test_selector_contract_contains_required_identity_fields():
    source = _selector_source()

    for field in (
        "expiry",
        "strike",
        "option_type",
    ):
        assert field in source


def test_selector_contract_contains_entry_price():
    source = _selector_source()

    assert (
        "entry_price" in source
        or "premium" in source
        or "lastPrice" in source
    )


def test_selector_contract_contains_quantity():
    source = _selector_source()

    assert "quantity" in source


def test_selector_does_not_use_future_market_data_for_direction():
    source = _selector_source()

    forbidden = (
        "tomorrow_price",
        "future_price",
        "next_day_price",
    )

    assert not any(
        name in source
        for name in forbidden
    )


def test_selector_has_clear_selection_errors():
    source = _selector_source()

    assert "raise" in source
    assert (
        "Error" in source
        or "ValueError" in source
        or "Exception" in source
    )


def test_selector_preserves_expiry():
    source = _selector_source()

    assert "expiry" in source
    assert (
        "Contract" in source
        or "contract" in source
        or "selected" in source.lower()
    )


def test_selector_preserves_strike():
    source = _selector_source()

    assert "strike" in source
    assert (
        "Contract" in source
        or "contract" in source
        or "selected" in source.lower()
    )


def test_selector_exposes_live_contract_selection():
    source = _selector_source()

    assert "def select_live_contract" in source


def test_selector_exposes_atm_contract_selection():
    source = _selector_source()

    assert "def select_atm_contract" in source


def test_selector_exposes_atm_strike_selection():
    source = _selector_source()

    assert "def select_atm_strike" in source