import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { BrainCircuit, RefreshCcw, Save, Search, ShieldCheck, Trash2 } from "lucide-react";

import { api } from "../api/client";
import { formatRequestError } from "../api/errors";
import { ToolbarButton } from "../components/ToolbarButton";
import type { AgentMemory, AgentPlanPreview, AgentPlannerPolicy, AgentSkill } from "../types";

const DEFAULT_MEMORY: AgentMemory = {
  id: "mem_new_rule",
  type: "workflow_rule",
  scope: "agent",
  title: "",
  content: "",
  tags: [],
  source: "user",
  confidence: "medium",
  enabled: true,
  expires_at: null
};

const DEFAULT_SKILL: AgentSkill = {
  id: "new_skill",
  title: "",
  description: "",
  trigger_terms: [],
  steps: [],
  allowed_tools: [],
  required_confirmations: [],
  output_format: "agent_report",
  enabled: true
};

export function AgentGovernancePage() {
  const [memories, setMemories] = useState<AgentMemory[]>([]);
  const [skills, setSkills] = useState<AgentSkill[]>([]);
  const [policy, setPolicy] = useState<AgentPlannerPolicy | null>(null);
  const [memoryDraft, setMemoryDraft] = useState<AgentMemory>(DEFAULT_MEMORY);
  const [skillDraft, setSkillDraft] = useState<AgentSkill>(DEFAULT_SKILL);
  const [prompt, setPrompt] = useState("给我这周股票扫描结果并完成分享的最终结果");
  const [preview, setPreview] = useState<AgentPlanPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("等待治理数据");

  async function refresh() {
    const [memoryPayload, skillPayload, policyPayload] = await Promise.all([api.agentMemories(), api.agentSkills(), api.agentPolicy()]);
    setMemories(memoryPayload.memories);
    setSkills(skillPayload.skills);
    setPolicy(policyPayload.policy);
  }

  useEffect(() => {
    void refresh().catch((error) => setMessage(formatRequestError(error)));
  }, []);

  async function runTask(label: string, action: () => Promise<void>) {
    setBusy(true);
    setMessage(`${label}...`);
    try {
      await action();
      setMessage(`${label}完成`);
    } catch (error) {
      setMessage(formatRequestError(error));
    } finally {
      setBusy(false);
    }
  }

  async function saveMemory() {
    const payload = normalizeMemoryDraft(memoryDraft);
    if (!payload.id || !payload.title || !payload.content) return;
    await runTask("保存Memory", async () => {
      const response = await api.createAgentMemory(payload);
      setMemories((current) => [response.memory, ...current.filter((item) => item.id !== response.memory.id)]);
    });
  }

  async function removeMemory(memoryId: string) {
    await runTask("删除Memory", async () => {
      await api.deleteAgentMemory(memoryId);
      setMemories((current) => current.filter((item) => item.id !== memoryId));
    });
  }

  async function toggleMemory(memory: AgentMemory) {
    await runTask("更新Memory", async () => {
      const response = await api.updateAgentMemory(memory.id, { enabled: !memory.enabled });
      setMemories((current) => current.map((item) => (item.id === memory.id ? response.memory : item)));
    });
  }

  async function saveSkill() {
    const payload = normalizeSkillDraft(skillDraft);
    if (!payload.id || !payload.title || !payload.steps.length) return;
    await runTask("保存Skill", async () => {
      const response = await api.createAgentSkill(payload);
      setSkills((current) => [response.skill, ...current.filter((item) => item.id !== response.skill.id)]);
    });
  }

  async function savePolicy() {
    if (!policy) return;
    await runTask("保存Planner Policy", async () => {
      const response = await api.updateAgentPolicy(policy);
      setPolicy(response.policy);
    });
  }

  async function previewPlan() {
    await runTask("预览计划", async () => {
      const response = await api.previewAgentPlan(prompt, { source: "frontend" });
      setPreview(response.preview);
    });
  }

  return (
    <div className="agent-governance-page">
      <section className="panel governance-hero">
        <div>
          <div className="panel-title">Agent治理</div>
          <p className="muted-copy">Memory、Skills 和 Planner Policy 会决定 Agent 如何理解任务、选择工具、等待确认并返回结果。</p>
        </div>
        <div className="toolbar-row">
          <ToolbarButton icon={<RefreshCcw size={15} />} onClick={() => void runTask("刷新治理数据", refresh)} disabled={busy}>
            刷新
          </ToolbarButton>
        </div>
      </section>

      <div className="governance-grid">
        <section className="panel governance-section">
          <SectionTitle icon={<BrainCircuit size={16} />} title="Memory" />
          <div className="governance-list">
            {memories.map((memory) => (
              <article className="governance-row" key={memory.id}>
                <div>
                  <strong>{memory.title}</strong>
                  <span>{memory.id} · {memory.type} · {memory.confidence}</span>
                  <p>{memory.content}</p>
                </div>
                <div className="toolbar-row">
                  <ToolbarButton onClick={() => void toggleMemory(memory)} disabled={busy}>
                    {memory.enabled ? "启用" : "停用"}
                  </ToolbarButton>
                  <ToolbarButton icon={<Trash2 size={14} />} onClick={() => void removeMemory(memory.id)} disabled={busy}>
                    删除
                  </ToolbarButton>
                </div>
              </article>
            ))}
          </div>
          <div className="governance-editor">
            <input aria-label="Memory ID" value={memoryDraft.id} onChange={(event) => setMemoryDraft({ ...memoryDraft, id: event.currentTarget.value })} />
            <input aria-label="Memory标题" placeholder="Memory标题" value={memoryDraft.title} onChange={(event) => setMemoryDraft({ ...memoryDraft, title: event.currentTarget.value })} />
            <textarea aria-label="Memory内容" placeholder="Memory内容" rows={3} value={memoryDraft.content} onChange={(event) => setMemoryDraft({ ...memoryDraft, content: event.currentTarget.value })} />
            <input aria-label="Memory标签" placeholder="weekly,scan" value={memoryDraft.tags.join(",")} onChange={(event) => setMemoryDraft({ ...memoryDraft, tags: splitCsv(event.currentTarget.value) })} />
            <ToolbarButton variant="primary" icon={<Save size={15} />} onClick={() => void saveMemory()} disabled={busy}>
              保存Memory
            </ToolbarButton>
          </div>
        </section>

        <section className="panel governance-section">
          <SectionTitle icon={<ShieldCheck size={16} />} title="Skills" />
          <div className="governance-list">
            {skills.map((skill) => (
              <article className="governance-row" key={skill.id}>
                <div>
                  <strong>{skill.id}</strong>
                  <span>{skill.title} · {skill.output_format}</span>
                  <p>{skill.steps.join(" -> ")}</p>
                </div>
              </article>
            ))}
          </div>
          <div className="governance-editor">
            <input aria-label="Skill ID" value={skillDraft.id} onChange={(event) => setSkillDraft({ ...skillDraft, id: event.currentTarget.value })} />
            <input aria-label="Skill标题" placeholder="Skill标题" value={skillDraft.title} onChange={(event) => setSkillDraft({ ...skillDraft, title: event.currentTarget.value })} />
            <textarea aria-label="Skill描述" placeholder="Skill描述" rows={2} value={skillDraft.description} onChange={(event) => setSkillDraft({ ...skillDraft, description: event.currentTarget.value })} />
            <input aria-label="触发词" placeholder="触发词，用逗号分隔" value={skillDraft.trigger_terms.join(",")} onChange={(event) => setSkillDraft({ ...skillDraft, trigger_terms: splitCsv(event.currentTarget.value) })} />
            <input aria-label="步骤工具" placeholder="步骤工具，用逗号分隔" value={skillDraft.steps.join(",")} onChange={(event) => setSkillDraft({ ...skillDraft, steps: splitCsv(event.currentTarget.value), allowed_tools: splitCsv(event.currentTarget.value) })} />
            <ToolbarButton variant="primary" icon={<Save size={15} />} onClick={() => void saveSkill()} disabled={busy}>
              保存Skill
            </ToolbarButton>
          </div>
        </section>

        <section className="panel governance-section">
          <SectionTitle icon={<ShieldCheck size={16} />} title="Planner Policy" />
          {policy ? (
            <div className="governance-editor">
              <label className="field compact-field">
                <span>最大步骤数</span>
                <input value={policy.max_steps} onChange={(event) => setPolicy({ ...policy, max_steps: Number(event.currentTarget.value) || 1 })} />
              </label>
              <label className="field compact-field">
                <span>阻断意图</span>
                <input value={policy.blocked_intents.join(",")} onChange={(event) => setPolicy({ ...policy, blocked_intents: splitCsv(event.currentTarget.value) })} />
              </label>
              <label className="field compact-field">
                <span>默认输出</span>
                <input value={policy.default_output_format} onChange={(event) => setPolicy({ ...policy, default_output_format: event.currentTarget.value })} />
              </label>
              <div className="permission-map">
                {Object.entries(policy.tool_permissions).map(([tool, permission]) => (
                  <span className={`tool-pill permission-${permission}`} key={tool}>{tool} · {permission}</span>
                ))}
              </div>
              <ToolbarButton variant="primary" icon={<Save size={15} />} onClick={() => void savePolicy()} disabled={busy}>
                保存Policy
              </ToolbarButton>
            </div>
          ) : <p className="muted-copy">正在加载策略。</p>}
        </section>

        <section className="panel governance-section">
          <SectionTitle icon={<Search size={16} />} title="Plan Preview" />
          <textarea aria-label="预览Prompt" rows={4} value={prompt} onChange={(event) => setPrompt(event.currentTarget.value)} />
          <ToolbarButton variant="primary" icon={<Search size={15} />} onClick={() => void previewPlan()} disabled={busy}>
            预览计划
          </ToolbarButton>
          {preview ? <PlanPreviewCard preview={preview} /> : <p className="muted-copy">输入任务后预览 Agent 会读取什么、选择哪个 Skill、调用哪些工具。</p>}
        </section>
      </div>
      <p className="muted-copy">{message}</p>
    </div>
  );
}

function SectionTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="governance-section-title">
      {icon}
      <strong>{title}</strong>
    </div>
  );
}

function PlanPreviewCard({ preview }: { preview: AgentPlanPreview }) {
  return (
    <div className={`plan-preview-card status-${preview.status}`}>
      <div className="task-meta">
        <span>intent: {preview.intent}</span>
        <span>final: {preview.final_output}</span>
      </div>
      {preview.selected_skill ? <p><strong>Skill:</strong> {preview.selected_skill.id} · {preview.selected_skill.title}</p> : null}
      {preview.blocked_reason ? <p className="warning-copy">{preview.blocked_reason}</p> : null}
      <div className="agent-timeline">
        {preview.steps.map((step) => (
          <div className={`agent-step status-${step.permission}`} key={`${step.index}-${step.tool}`}>
            <ShieldCheck size={14} />
            <div>
              <strong>{step.tool}</strong>
              <span>{step.permission} · {step.reason}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="agent-evidence">
        {preview.matched_memories.map((memory) => <span key={memory.id}>Memory: {memory.title}</span>)}
        {preview.stop_conditions.map((condition) => <span key={condition}>Stop: {condition}</span>)}
      </div>
    </div>
  );
}

function normalizeMemoryDraft(memory: AgentMemory): AgentMemory {
  return { ...memory, id: memory.id.trim(), title: memory.title.trim(), content: memory.content.trim(), tags: memory.tags.filter(Boolean) };
}

function normalizeSkillDraft(skill: AgentSkill): AgentSkill {
  const steps = skill.steps.filter(Boolean);
  return { ...skill, id: skill.id.trim(), title: skill.title.trim(), description: skill.description.trim(), steps, allowed_tools: skill.allowed_tools.length ? skill.allowed_tools : steps };
}

function splitCsv(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}
