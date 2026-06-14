import { AlertTriangle, CheckCircle2 } from "lucide-react";

import type { AIInsight, PlatformSettings, PortfolioRequest, RiskStatus } from "../types";

type Props = {
  insight: AIInsight | null;
  riskStatus: RiskStatus | null;
  settings: PlatformSettings;
  portfolio: PortfolioRequest;
  onSettingsChange: (settings: PlatformSettings) => void;
  onPortfolioChange: (portfolio: PortfolioRequest) => void;
};

type InfoSummary = {
  category: string;
  description: string;
  importance: "高" | "中" | "低";
};

const DEFAULT_INFORMATION: InfoSummary[] = [
  { category: "资金面", description: "等待信息面摘要。", importance: "中" },
  { category: "政策面", description: "等待政策、公告或行业事件。", importance: "低" },
  { category: "事件面", description: "生成AI观点后会同步证据链。", importance: "低" }
];

export function InspectorPanel({ insight, riskStatus, settings, portfolio, onSettingsChange, onPortfolioChange }: Props) {
  const direction = insight ? directionLabel(insight.direction) : "等待";
  const confidence = insight ? `${insight.confidence}%` : "-";
  const directionClass = insight ? normalizedDirection(insight.direction) : "waiting";
  const information = informationSummaries(insight);
  const riskEnabled = settings.risk_enabled;
  const riskFooter = riskFooterText(riskStatus, riskEnabled);

  const updateNumber = (key: "max_drawdown_pct" | "max_order_cash" | "max_position_shares", raw: string) => {
    onSettingsChange({ ...settings, [key]: raw === "" ? 0 : Number(raw) });
  };

  const updateAiScoring = (checked: boolean) => {
    onPortfolioChange({
      ...portfolio,
      ai_adjust: checked,
      ai_direction: checked ? normalizedDirection(insight?.direction) : null
    });
  };

  return (
    <aside className="inspector">
      <div className="inspector-header">
        <strong>AI研究员</strong>
        <label className="compact-switch">
          <span>AI参与评分</span>
          <input aria-label="AI参与评分" type="checkbox" checked={portfolio.ai_adjust} onChange={(event) => updateAiScoring(event.currentTarget.checked)} />
        </label>
      </div>
      <div className="tabs">
        <button>技术指标</button>
        <button className="active">信息面摘要</button>
        <button>AI观点</button>
      </div>

      <section className="inspector-card">
        <div className="panel-title compact-title">信息面摘要</div>
        <div className="information-list">
          {information.map((item) => (
            <div className="information-item" key={`${item.category}-${item.description}`}>
              <span className="info-category">{item.category}</span>
              <p>{item.description}</p>
              <strong className={`importance importance-${item.importance}`}>{item.importance}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="inspector-card">
        <span className="caption">AI观点（基于技术 + 信息面综合）</span>
        <div className={`ai-direction ${directionClass}`}>
          <strong>{direction}</strong>
          <span>
            置信度 <b>{confidence}</b>
          </span>
        </div>
        <p>{insight?.suggested_action ?? "生成观点后，这里会展示建议动作与证据链。"}</p>
        <ul>
          {(insight?.technical_evidence ?? ["等待技术指标快照。"]).slice(0, 3).map((item) => (
            <li key={item}>
              <CheckCircle2 size={14} /> {item}
            </li>
          ))}
        </ul>
        <div className="risk-note">
          <AlertTriangle size={15} />
          {(insight?.risk_warnings ?? ["AI观点不能绕过确定性风控。"])[0]}
        </div>
      </section>

      <section className="inspector-card risk-editor">
        <div className="panel-title compact-title">风险阈值</div>
        <label className="field row-field">
          <span>启用风控</span>
          <input aria-label="启用风控" type="checkbox" checked={riskEnabled} onChange={(event) => onSettingsChange({ ...settings, risk_enabled: event.currentTarget.checked })} />
        </label>
        <label className="field">
          <span>最大回撤阈值</span>
          <input aria-label="最大回撤阈值" type="number" value={settings.max_drawdown_pct} onChange={(event) => updateNumber("max_drawdown_pct", event.currentTarget.value)} />
        </label>
        <label className="field">
          <span>单笔最大金额</span>
          <input aria-label="单笔最大金额" type="number" value={settings.max_order_cash} onChange={(event) => updateNumber("max_order_cash", event.currentTarget.value)} />
        </label>
        <label className="field">
          <span>持仓集中度</span>
          <input aria-label="持仓集中度" type="number" value={settings.max_position_shares} onChange={(event) => updateNumber("max_position_shares", event.currentTarget.value)} />
        </label>
        <label className="field">
          <span>止损模式</span>
          <select
            aria-label="止损模式"
            value={settings.stop_loss_mode}
            onChange={(event) => onSettingsChange({ ...settings, stop_loss_mode: event.currentTarget.value as PlatformSettings["stop_loss_mode"] })}
          >
            <option value="fixed_pct">固定比例</option>
            <option value="trailing">移动止损</option>
            <option value="manual">手动复核</option>
          </select>
        </label>
        <div className={riskStatus?.ok === false ? "risk-footer negative" : "risk-footer positive"}>{riskFooter}</div>
        <ul>
          {(riskStatus?.warnings?.length ? riskStatus.warnings : ["未触发主要风控警示。"]).map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      </section>
    </aside>
  );
}

function directionLabel(direction: string): string {
  if (direction === "bullish") return "看多";
  if (direction === "bearish") return "看空";
  if (direction === "neutral") return "中性";
  return "等待";
}

function normalizedDirection(direction: string | null | undefined): "bullish" | "bearish" | "neutral" {
  if (direction === "bullish" || direction === "bearish") return direction;
  return "neutral";
}

function informationSummaries(insight: AIInsight | null): InfoSummary[] {
  if (!insight?.information_evidence.length) return DEFAULT_INFORMATION;
  return insight.information_evidence.slice(0, 3).map((description, index) => ({
    category: informationCategory(description, index),
    description,
    importance: importanceFor(index, insight.confidence)
  }));
}

function informationCategory(description: string, index: number): string {
  if (description.includes("资金") || description.includes("流动性")) return "资金面";
  if (description.includes("政策") || description.includes("监管")) return "政策面";
  if (description.includes("业绩") || description.includes("公告")) return "公司面";
  return ["资金面", "政策面", "事件面"][index] ?? "事件面";
}

function importanceFor(index: number, confidence: number): "高" | "中" | "低" {
  if (index === 0 && confidence >= 70) return "高";
  if (index <= 1 && confidence >= 50) return "中";
  return "低";
}

function riskFooterText(riskStatus: RiskStatus | null, riskEnabled: boolean): string {
  if (!riskEnabled || riskStatus?.enabled === false) return "停用：风控当前关闭";
  if (riskStatus?.ok === false) return `未通过：${riskStatus.warnings[0] ?? "需要关注"}`;
  return "通过：未触发主要风控警示";
}
