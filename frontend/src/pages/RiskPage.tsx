import { DataTable } from "../components/DataTable";
import { ToolbarButton } from "../components/ToolbarButton";
import type { PageProps } from "./pageTypes";
import type { PlatformSettings } from "../types";

export function RiskPage({ state, actions }: PageProps) {
  const updateSettings = (patch: Partial<PlatformSettings>) => actions.setSettings({ ...state.settings, ...patch });
  const updateNumber = (key: "max_drawdown_pct" | "max_order_cash" | "min_cash_balance" | "max_position_shares", raw: string) => {
    updateSettings({ [key]: raw === "" ? 0 : Number(raw) });
  };

  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">风控设置</div>
        <label className="field row-field">
          <span>启用风控</span>
          <input aria-label="启用风控" type="checkbox" checked={state.settings.risk_enabled} onChange={(event) => updateSettings({ risk_enabled: event.currentTarget.checked })} />
        </label>
        <label className="field">
          <span>最大回撤阈值</span>
          <input
            aria-label="最大回撤阈值"
            type="number"
            value={state.settings.max_drawdown_pct}
            onChange={(event) => updateNumber("max_drawdown_pct", event.currentTarget.value)}
          />
        </label>
        <label className="field">
          <span>单笔最大金额</span>
          <input aria-label="单笔最大金额" type="number" value={state.settings.max_order_cash} onChange={(event) => updateNumber("max_order_cash", event.currentTarget.value)} />
        </label>
        <label className="field">
          <span>最小现金余额</span>
          <input
            aria-label="最小现金余额"
            type="number"
            value={state.settings.min_cash_balance}
            onChange={(event) => updateNumber("min_cash_balance", event.currentTarget.value)}
          />
        </label>
        <label className="field">
          <span>最大持仓股数</span>
          <input
            aria-label="最大持仓股数"
            type="number"
            value={state.settings.max_position_shares}
            onChange={(event) => updateNumber("max_position_shares", event.currentTarget.value)}
          />
        </label>
        <label className="field">
          <span>止损模式</span>
          <select
            aria-label="止损模式"
            value={state.settings.stop_loss_mode}
            onChange={(event) => updateSettings({ stop_loss_mode: event.currentTarget.value as PlatformSettings["stop_loss_mode"] })}
          >
            <option value="fixed_pct">固定比例</option>
            <option value="trailing">移动止损</option>
            <option value="manual">手动复核</option>
          </select>
        </label>
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
