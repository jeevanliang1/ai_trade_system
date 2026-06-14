def test_web_app_imports():
    import ai_trade_system.web.app as app

    assert callable(app.main)


def test_stock_option_label_is_searchable_and_human_readable():
    from ai_trade_system.stock_catalog import StockInfo
    from ai_trade_system.web.app import _stock_option_label

    assert _stock_option_label(StockInfo("000001", "平安银行", "SZSE")) == "000001 平安银行 SZSE"


def test_sync_csv_path_for_symbol_resets_path_when_selected_stock_changes():
    from ai_trade_system.web.app import _sync_csv_path_for_symbol

    session_state = {
        "market_csv_symbol": "000001",
        "market_csv_path": "data/000001_daily.csv",
    }

    key = _sync_csv_path_for_symbol(session_state, "601318")

    assert key == "market_csv_path"
    assert session_state["market_csv_symbol"] == "601318"
    assert session_state["market_csv_path"] == "data/601318_daily.csv"
