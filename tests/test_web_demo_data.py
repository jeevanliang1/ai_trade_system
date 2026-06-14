from ai_trade_system.web.app import _demo_bars


def test_demo_bars_create_deterministic_local_research_data():
    bars = _demo_bars("000001", "SZSE", count=30)

    assert len(bars) == 30
    assert bars[0].symbol == "000001"
    assert bars[-1].close_price != bars[0].close_price
