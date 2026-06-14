import { useState } from "react";
import { Plus, ShieldCheck, Trash2 } from "lucide-react";

import { MetricStrip } from "../components/MetricStrip";
import { SegmentedControl } from "../components/SegmentedControl";
import { ToolbarButton } from "../components/ToolbarButton";
import type { PageProps } from "./pageTypes";

type EvidenceGroupProps = {
  title: string;
  items: string[];
  emptyText: string;
  tone: "technical" | "information" | "risk";
};

export function AIPage({ state, actions }: PageProps) {
  const [mode, setMode] = useState("balanced");
  const [horizon, setHorizon] = useState("5个交易日");
  const [notes, setNotes] = useState(["政策支持流动性改善", "行业景气度回升", "关注短线追高风险"]);
  const noteList = notes.map((item) => item.trim()).filter(Boolean);
  const updateNote = (index: number, value: string) => {
    setNotes((current) => current.map((note, noteIndex) => (noteIndex === index ? value : note)));
  };
  const addNote = () => setNotes((current) => [...current, ""]);
  const removeNote = (index: number) => {
    setNotes((current) => (current.length === 1 ? [""] : current.filter((_, noteIndex) => noteIndex !== index)));
  };

  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">AI研究员</div>
        <SegmentedControl
          value={mode}
          onChange={setMode}
          options={[
            { label: "平衡", value: "balanced" },
            { label: "保守", value: "conservative" },
            { label: "进攻", value: "aggressive" }
          ]}
        />
        <label className="field">
          <span>研究周期</span>
          <select value={horizon} onChange={(event) => setHorizon(event.currentTarget.value)}>
            <option>3个交易日</option>
            <option>5个交易日</option>
            <option>20个交易日</option>
          </select>
        </label>
        <div className="recent-notes-editor">
          <div className="recent-notes-header">
            <span className="field-label">信息面摘要</span>
            <ToolbarButton icon={<Plus size={14} />} onClick={addNote}>
              新增信息面摘要
            </ToolbarButton>
          </div>
          {notes.map((note, index) => (
            <div className="recent-note-row" key={index}>
              <label className="field">
                <span>{`信息面摘要 ${index + 1}`}</span>
                <input value={note} onChange={(event) => updateNote(index, event.currentTarget.value)} />
              </label>
              <button className="icon-button" aria-label={`删除信息面摘要 ${index + 1}`} onClick={() => removeNote(index)} disabled={notes.length === 1}>
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
        <ToolbarButton variant="primary" onClick={() => actions.researchAI(noteList, mode, horizon)}>
          生成AI观点
        </ToolbarButton>
      </section>
      <section className="main-column">
        <MetricStrip
          metrics={[
            { label: "方向", value: state.insight?.direction ?? "-" },
            { label: "置信度", value: state.insight ? `${state.insight.confidence}%` : "-" },
            { label: "建议动作", value: state.insight?.suggested_action ?? "-" }
          ]}
        />
        <section className="provider-boundary-panel" aria-label="Provider边界">
          <div className="provider-boundary-icon">
            <ShieldCheck size={16} />
          </div>
          <div>
            <div className="provider-boundary-title">Provider边界</div>
            <p>
              MockLLMProvider 仅生成研究观点，用于回测/纸面交易前的人工复核；不会下单，不能绕过风控、纸面执行或未来实盘前置规则。
            </p>
          </div>
        </section>
        <section className="panel">
          <div className="panel-title">证据链</div>
          <div className="evidence-grid">
            <EvidenceGroup title="技术证据" tone="technical" items={state.insight?.technical_evidence ?? []} emptyText="生成观点后显示技术指标、价格结构和信号证据。" />
            <EvidenceGroup title="信息面证据" tone="information" items={state.insight?.information_evidence ?? []} emptyText="生成观点后显示信息面摘要如何影响判断。" />
            <EvidenceGroup title="风险提示" tone="risk" items={state.insight?.risk_warnings ?? []} emptyText="生成观点后显示需要优先复核的风险。" />
          </div>
        </section>
        {state.aiPrompt ? (
          <details className="prompt-snapshot-panel">
            <summary>生成 Prompt 快照</summary>
            <pre>{state.aiPrompt}</pre>
          </details>
        ) : null}
      </section>
    </div>
  );
}

function EvidenceGroup({ title, items, emptyText, tone }: EvidenceGroupProps) {
  return (
    <section className={`evidence-group evidence-${tone}`}>
      <div className="evidence-group-title">{title}</div>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>{emptyText}</p>
      )}
    </section>
  );
}
