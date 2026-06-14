import { DataTable } from "../components/DataTable";
import { ToolbarButton } from "../components/ToolbarButton";
import type { PageProps } from "./pageTypes";
import type { PlatformSettings } from "../types";

type RiskWarningView = {
  severity: "高" | "中" | "信息";
  tone: "high" | "medium" | "info";
  warning: string;
  hint: string;
};

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
        <RiskExamplePanel state={state} />
        <section className="panel" aria-label="风控状态明细">
          <div className="panel-title">风控状态</div>
          <p className={riskStatusOk(state) ? "positive" : "negative"}>{riskStatusOk(state) ? "当前已通过风控校验" : "当前存在风控警示"}</p>
          <RiskWarningList rows={riskWarningViews(state)} />
        </section>
      </section>
    </div>
  );
}

function RiskWarningList({ rows }: { rows: RiskWarningView[] }) {
  return (
    <div className="risk-warning-list">
      {rows.map((row) => (
        <article className={`risk-warning-row ${row.tone}`} key={`${row.warning}-${row.hint}`}>
          <span className="risk-severity">{row.severity}</span>
          <strong>{row.warning}</strong>
          <small>{row.hint}</small>
        </article>
      ))}
    </div>
  );
}

function riskStatusOk(state: PageProps["state"]) {
  if (!state.settings.risk_enabled || state.riskStatus?.enabled === false) return true;
  return state.riskStatus?.ok !== false;
}

function riskWarningViews(state: PageProps["state"]): RiskWarningView[] {
  if (!state.settings.risk_enabled || state.riskStatus?.enabled === false) {
    return [{ severity: "信息", tone: "info", warning: "风控已关闭", hint: "开启风控后再评估" }];
  }
  const warnings = state.riskStatus?.warnings ?? [];
  if (!warnings.length) {
    return [{ severity: "信息", tone: "info", warning: "未触发主要风控警示。", hint: "保持当前阈值并定期复核" }];
  }
  return warnings.map((warning) => {
    const severity = riskWarningSeverity(warning);
    return {
      severity,
      tone: severity === "高" ? "high" : severity === "中" ? "medium" : "info",
      warning,
      hint: riskRemediationHint(warning)
    };
  });
}

function riskWarningSeverity(warning: string): RiskWarningView["severity"] {
  if (warning.includes("最大回撤") || warning.toLowerCase().includes("drawdown")) return "高";
  if (warning.includes("单笔") || warning.includes("现金") || warning.includes("持仓") || warning.includes("仓位")) return "中";
  return "信息";
}

function riskRemediationHint(warning: string) {
  if (warning.includes("最大回撤") || warning.toLowerCase().includes("drawdown")) return "降低仓位或收紧止损";
  if (warning.includes("单笔")) return "降低单笔最大金额或拆分订单";
  if (warning.includes("现金")) return "提高现金保留或减少开仓";
  if (warning.includes("持仓") || warning.includes("仓位")) return "降低最大持仓股数或分散标的";
  return "人工复核该风险项";
}

function RiskExamplePanel({ state }: { state: PageProps["state"] }) {
  if (!state.backtest) {
    return (
      <section className="panel risk-example-panel" aria-label="风控评估样例">
        <div className="panel-title">评估样例</div>
        <div className="backtest-empty-state">
          <strong>暂无回测指标</strong>
          <span>等待回测中心生成最大回撤、交易次数和胜率等输入。</span>
        </div>
      </section>
    );
  }

  const metrics = state.backtest.metrics;
  const rows = [
    {
      评估项: "最大回撤",
      API字段: "max_drawdown_pct",
      当前输入: formatPercent(metrics.max_drawdown_pct),
      活跃阈值: formatThresholdPercent(state.settings.max_drawdown_pct)
    },
    {
      评估项: "交易次数",
      API字段: "trade_count",
      当前输入: String(metrics.trade_count),
      活跃阈值: "观察项"
    },
    {
      评估项: "胜率",
      API字段: "win_rate_pct",
      当前输入: metrics.win_rate_pct == null ? "-" : formatPercent(metrics.win_rate_pct),
      活跃阈值: "观察项"
    },
    {
      评估项: "风控开关",
      API字段: "enabled",
      当前输入: state.settings.risk_enabled ? "开启" : "关闭",
      活跃阈值: state.settings.risk_enabled ? "生效" : "停用"
    }
  ];

  return (
    <section className="panel risk-example-panel" aria-label="风控评估样例">
      <div className="panel-title">评估样例</div>
      <DataTable rows={rows} />
    </section>
  );
}

function formatPercent(value: number) {
  return `${value.toFixed(2)}%`;
}

function formatThresholdPercent(value: number) {
  return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(2)}%`;
}
