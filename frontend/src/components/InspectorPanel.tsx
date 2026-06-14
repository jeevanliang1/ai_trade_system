import { AlertTriangle, CheckCircle2 } from "lucide-react";

import type { AIInsight, RiskStatus } from "../types";

type Props = {
  insight: AIInsight | null;
  riskStatus: RiskStatus | null;
};

export function InspectorPanel({ insight, riskStatus }: Props) {
  const direction = insight ? directionLabel(insight.direction) : "等待观点";
  const confidence = insight ? `${insight.confidence}%` : "-";
  return (
    <aside className="inspector">
      <div className="inspector-header">
        <strong>AI研究员</strong>
        <span>AI参与评分</span>
      </div>
      <div className="tabs">
        <button>技术指标</button>
        <button className="active">信息面摘要</button>
        <button>AI观点</button>
      </div>
      <section className="inspector-card">
        <span className="caption">AI观点（基于技术 + 信息面综合）</span>
        <div className={`ai-direction ${insight?.direction ?? "neutral"}`}>
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
      <section className="inspector-card">
        <div className="panel-title">风险阈值</div>
        {riskStatus?.ok ? <p className="positive">当前配置通过风险校验</p> : <p className="negative">风险状态需要关注</p>}
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
  return "中性";
}
