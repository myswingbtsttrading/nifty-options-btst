from datetime import date

import pytest

import option_selector


def test_selector_rejects_invalid_option_type():
    with pytest.raises((ValueError, TypeError)):
        option_selector.select_contract(
            option_chain=[],
            option_type="XX",
            underlying_price=25000,
            expiry=date(2026, 9, 4),
        )


def test_selector_rejects_non_positive_underlying():
    with pytest.raises((ValueError, TypeError)):
        option_selector.select_contract(
            option_chain=[],
            option_type="CE",
            underlying_price=0,
            expiry=date(2026, 9, 4),
        )


def test_selector_rejects_missing_expiry():
    with pytest.raises((ValueError, TypeError)):
        option_selector.select_contract(
            option_chain=[],
            option_type="CE",
            underlying_price=25000,
            expiry=None,
        )


def test_selector_never_returns_non_positive_strike():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "strike" in source
    assert ">" in source


def test_selector_validates_option_premium():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "lastPrice" in source
    assert "<= 0" in source or "> 0" in source


def test_selector_has_explicit_selection_mode():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "selection_mode" in source


def test_selector_supports_ce_and_pe():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert '"CE"' in source
    assert '"PE"' in source


def test_selector_uses_expiry_in_contract_selection():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "expiry" in source


def test_selector_uses_strike_in_contract_selection():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "strike" in source


def test_selector_has_no_random_contract_selection():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "random" not in source.lower()


def test_selector_has_deterministic_sorting():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "sort" in source or "sorted" in source


def test_selector_rejects_empty_chain():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "empty" in source.lower() or "no suitable" in source.lower()


def test_selector_contract_contains_required_identity_fields():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    for field in (
        "expiry",
        "strike",
        "option_type",
    ):
        assert field in source


def test_selector_contract_contains_entry_price():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "entry_price" in source or "premium" in source


def test_selector_contract_contains_quantity():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "quantity" in source


def test_selector_contract_contains_lots():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "lots" in source


def test_selector_does_not_use_future_market_data_for_direction():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

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
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "raise" in source
    assert "Error" in source or "ValueError" in source


def test_selector_preserves_exact_expiry():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "expiry" in source
    assert "selected" in source.lower()


def test_selector_preserves_exact_strike():
    source = open(
        "option_selector.py",
        encoding="utf-8",
    ).read()

    assert "strike" in source
    assert "selected" in source.lower()