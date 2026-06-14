import { Play } from "lucide-react";

import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { ToolbarButton } from "../components/ToolbarButton";
import { equityOption } from "./chartOptions";
import type { PageProps } from "./pageTypes";

export function PaperPage({ state, actions }: PageProps) {
  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">纸面交易</div>
        <label className="field">
          <span>事件日志</span>
          <input value={state.settings.log_path} onChange={(event) => actions.setSettings({ ...state.settings, log_path: event.currentTarget.value })} />
        </label>
        <ToolbarButton icon={<Play size={16} />} variant="success" onClick={() => actions.runPaper("single")}>
          运行纸面交易
        </ToolbarButton>
      </section>
      <section className="main-column">
        <ChartPanel
          title="纸面权益"
          option={equityOption(
            state.paper
              ? {
                  bars: [],
                  metrics: {} as never,
                  trades: [],
                  drawdowns: [],
                  risk_status: { ok: true, warnings: [], enabled: true },
                  equity_curve: state.paper.equity.map((row) => ({
                    trading_day: String(row.trading_day),
                    equity: Number(row.equity),
                    cash: Number(row.cash)
                  }))
                }
              : null
          )}
          height={320}
        />
        <section className="panel">
          <div className="panel-title">订单事件</div>
          <DataTable rows={(state.paper?.orders ?? []) as Record<string, unknown>[]} />
        </section>
      </section>
    </div>
  );
}
