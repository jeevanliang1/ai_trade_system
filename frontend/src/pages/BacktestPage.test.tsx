import { render, screen } from "@testing-library/react";

import { BacktestResultPanel } from "./BacktestPage";
import type { BacktestResponse } from "../types";

test("BacktestResultPanel renders metrics, chart title, and trade table", () => {
  const result: BacktestResponse = {
    bars: [],
    metrics: {
      final_equity: 112000,
      total_return_pct: 12,
      annualized_return_pct: 18,
      max_drawdown_pct: -6,
      trade_count: 2,
      win_rate_pct: 50,
      profit_factor: 1.8,
      exposure_pct: 40
    },
    equity_curve: [{ trading_day: "2024-01-02", equity: 100000, cash: 80000, close_price: 10 }],
    drawdowns: [{ trading_day: "2024-01-02", equity: 100000, drawdown_pct: 0 }],
    trades: [{ trading_day: "2024-01-02", side: "buy", symbol: "000001", price: 10, volume: 100, commission: 0.3 }],
    risk_status: { ok: true, warnings: [], enabled: true }
  };

  render(<BacktestResultPanel result={result} />);

  expect(screen.getByText("112,000.00")).toBeInTheDocument();
  expect(screen.getByText("资金曲线")).toBeInTheDocument();
  expect(screen.getByText("交易明细")).toBeInTheDocument();
});
