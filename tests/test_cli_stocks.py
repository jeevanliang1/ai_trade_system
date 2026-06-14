import sys
from pathlib import Path

import pandas as pd

from ai_trade_system.cli import main


def test_cli_stocks_search_prints_name_code_and_exchange(monkeypatch, tmp_path: Path, capsys):
    catalog_path = tmp_path / "stocks.csv"
    catalog_path.write_text("code,name,exchange\n000001,平安银行,SZSE\n600000,浦发银行,SSE\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["ai-trade", "stocks", "search", "平安", "--catalog", str(catalog_path)])

    main()

    output = capsys.readouterr().out
    assert "000001" in output
    assert "平安银行" in output
    assert "SZSE" in output


def test_cli_stocks_refresh_writes_catalog(monkeypatch, tmp_path: Path, capsys):
    class FakeAkshare:
        @staticmethod
        def stock_info_a_code_name():
            return pd.DataFrame([{"code": "1", "name": "平安银行"}])

    monkeypatch.setitem(sys.modules, "akshare", FakeAkshare)
    output_path = tmp_path / "a_share_stocks.csv"
    monkeypatch.setattr(sys, "argv", ["ai-trade", "stocks", "refresh", "--output", str(output_path)])

    main()

    assert "wrote 1 stocks" in capsys.readouterr().out
    assert output_path.read_text(encoding="utf-8").splitlines() == [
        "code,name,exchange",
        "000001,平安银行,SZSE",
    ]
