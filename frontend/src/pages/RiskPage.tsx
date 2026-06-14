import { DataTable } from "../components/DataTable";
import { ToolbarButton } from "../components/ToolbarButton";
import type { PageProps } from "./pageTypes";

export function RiskPage({ state, actions }: PageProps) {
  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">风控设置</div>
        {[
          ["max_drawdown_pct", "最大回撤保护(%)"],
          ["max_order_cash", "单笔最大金额"],
          ["min_cash_balance", "最小现金余额"],
          ["max_position_shares", "最大持仓股数"]
        ].map(([key, label]) => (
          <label className="field" key={key}>
            <span>{label}</span>
            <input
              type="number"
              value={Number(state.settings[key as keyof typeof state.settings])}
              onChange={(event) => actions.setSettings({ ...state.settings, [key]: Number(event.currentTarget.value) })}
            />
          </label>
        ))}
        <ToolbarButton variant="primary" onClick={actions.evaluateRisk}>
          检查风控
        </ToolbarButton>
      </section>
      <section className="main-column">
        <section className="panel">
          <div className="panel-title">风控状态</div>
          <p className={state.riskStatus?.ok ? "positive" : "negative"}>{state.riskStatus?.ok ? "当前已通过风控校验" : "当前存在风控警示"}</p>
          <DataTable
            rows={(state.riskStatus?.warnings.length ? state.riskStatus.warnings : ["未触发主要风控警示。"]).map((warning) => ({ 风险项: warning }))}
          />
        </section>
      </section>
    </div>
  );
}
