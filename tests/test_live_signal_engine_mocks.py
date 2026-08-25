from datetime import date, datetime
from unittest.mock import patch

from live_signal_engine import (
    build_live_signal,
)
from live_market_data import (
    LiveOptionQuote,
    LiveUnderlyingQuote,
)
from option_chain_confirmation import (
    OptionChainSnapshot,
)


def _history():
    return [
        {
            "timestamp": datetime(
                2026,
                8,
                25,
                9,
                15,
            ),
            "close": 24000 + index * 12,
        }
        for index in range(60)
    ]


def test_build_live_signal_connects_market_layers():
    quote = LiveUnderlyingQuote(
        timestamp=datetime(
            2026,
            8,
            25,
            15,
            0,
        ),
        price=24750,
        previous_close=24600,
    )

    chain = {
        "records": {
            "timestamp": "25-Aug-2026 15:00:00",
            "expiryDates": [
                "27-Aug-2026",
            ],
            "data": [
                {
                    "strikePrice": 24750,
                    "expiryDate": "27-Aug-2026",
                    "CE": {
                        "openInterest": 1000,
                        "changeinOpenInterest": 200,
                        "totalTradedVolume": 1000,
                        "lastPrice": 100,
                    },
                    "PE": {
                        "openInterest": 1000,
                        "changeinOpenInterest": 100,
                        "totalTradedVolume": 800,
                        "lastPrice": 100,
                    },
                },
            ],
        }
    }

    chain_snapshot = OptionChainSnapshot(
        ce_oi=1000,
        pe_oi=1000,
        ce_oi_change=200,
        pe_oi_change=100,
        ce_volume=1000,
        pe_volume=800,
    )

    option_quote = LiveOptionQuote(
        timestamp=datetime(
            2026,
            8,
            25,
            15,
            0,
        ),
        expiry=date(
            2026,
            8,
            27,
        ),
        strike=24750,
        option_type="CE",
        price=100,
    )

    with patch(
        "live_signal_engine.fetch_nifty_quote",
        return_value=quote,
    ), patch(
        "live_signal_engine.fetch_nifty_option_chain",
        return_value=chain,
    ), patch(
        "live_signal_engine.build_option_chain_snapshot",
        return_value=chain_snapshot,
    ), patch(
        "live_signal_engine.find_option_quote",
        return_value=option_quote,
    ):
        result = build_live_signal(
            historical_rows=_history(),
            capital=100000,
            lot_size=65,
        )

    assert result.signal.nifty_price == 24750
    assert result.signal.entry_price == 100
    assert result.indicators.ema20 > 0
    assert result.indicators.ema50 > 0
    assert 0 <= result.indicators.rsi <= 100