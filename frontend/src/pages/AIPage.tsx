import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { SegmentedControl } from "../components/SegmentedControl";
import { ToolbarButton } from "../components/ToolbarButton";
import type { PageProps } from "./pageTypes";

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
        <section className="panel">
          <div className="panel-title">证据链</div>
          <DataTable
            rows={[
              ...(state.insight?.technical_evidence ?? []).map((value) => ({ 类型: "技术", 内容: value })),
              ...(state.insight?.information_evidence ?? []).map((value) => ({ 类型: "信息面", 内容: value })),
              ...(state.insight?.risk_warnings ?? []).map((value) => ({ 类型: "风险", 内容: value }))
            ]}
          />
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
