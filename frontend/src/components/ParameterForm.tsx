import { useEffect, useMemo, useState } from "react";

import type { StrategyParameter } from "../types";

type Control = StrategyParameter & {
  label?: string;
  options?: string[];
};

type Props = {
  parameters: StrategyParameter[];
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  onValidationChange?: (errors: Record<string, string>) => void;
};

const EXTRA_CONTROLS: Control[] = [
  {
    name: "rsi_period",
    label: "RSI周期",
    display_name: "RSI周期",
    annotation: "int",
    default: 14,
    description: "计算 RSI 指标时使用的回看天数。",
    increase_effect: "调大后 RSI 更平滑，信号更稳但反应更慢。",
    decrease_effect: "调小后 RSI 更敏感，能更早反应，但假信号更多。"
  },
  {
    name: "rsi_lower",
    label: "RSI下限",
    display_name: "RSI下限",
    annotation: "float",
    default: 30,
    description: "RSI 低于该值时更偏向超卖买入判断。",
    increase_effect: "调大后更容易触发买入，机会更多但质量可能下降。",
    decrease_effect: "调小后买入更严格，信号更少但更偏极端超卖。"
  },
  {
    name: "rsi_upper",
    label: "RSI上限",
    display_name: "RSI上限",
    annotation: "float",
    default: 70,
    description: "RSI 高于该值时更偏向超买卖出判断。",
    increase_effect: "调大后卖出更晚，可能吃到更多趋势，也可能回吐利润。",
    decrease_effect: "调小后卖出更早，保护利润更积极但可能过早离场。"
  },
  {
    name: "ma_type",
    label: "MA类型",
    display_name: "MA类型",
    annotation: "select",
    default: "SMA",
    options: ["SMA", "EMA", "WMA"],
    description: "选择均线计算方式，影响指标对近期价格的响应速度。",
    increase_effect: "这是枚举选项，不按调大理解；EMA 更偏近期价格，SMA 更平滑。",
    decrease_effect: "这是枚举选项，不按调小理解；切换前应比较回测结果。"
  },
  {
    name: "holding_period",
    label: "持仓周期",
    display_name: "持仓周期",
    annotation: "int",
    default: 20,
    description: "策略预期持仓或观察持仓的交易日数量。",
    increase_effect: "调大后持仓更久，更依赖中长期走势。",
    decrease_effect: "调小后周转更快，但交易频率和噪音影响会上升。"
  },
  {
    name: "stop_loss_pct",
    label: "止损比例",
    display_name: "止损比例",
    annotation: "float",
    default: 8,
    description: "亏损达到该比例时触发止损判断。",
    increase_effect: "调大后止损更宽松，持仓空间更大但单次亏损可能扩大。",
    decrease_effect: "调小后止损更严格，亏损控制更快但更容易被震荡洗出。"
  },
  {
    name: "take_profit_pct",
    label: "止盈比例",
    display_name: "止盈比例",
    annotation: "float",
    default: 18,
    description: "盈利达到该比例时触发止盈判断。",
    increase_effect: "调大后止盈目标更高，可能吃到更大行情但落袋更慢。",
    decrease_effect: "调小后更快锁定利润，但可能过早离场。"
  },
  {
    name: "max_order_size",
    label: "最大下单量",
    display_name: "最大下单量",
    annotation: "int",
    default: 1000,
    description: "单次交易允许提交的最大股数。",
    increase_effect: "调大后单笔仓位更重，收益和亏损都会放大。",
    decrease_effect: "调小后单笔仓位更轻，风险更低但收益弹性也更低。"
  },
  {
    name: "ai_score_threshold",
    label: "AI评分阈值",
    display_name: "AI评分阈值",
    annotation: "float",
    default: 65,
    description: "AI 评分达到该值后才允许更积极地参与策略判断。",
    increase_effect: "调大后 AI 参与更严格，触发更少。",
    decrease_effect: "调小后 AI 更容易参与，但低置信度建议也可能进入判断。"
  },
  {
    name: "ai_enabled",
    label: "启用AI评分",
    display_name: "启用AI评分",
    annotation: "bool",
    default: false,
    description: "控制是否让 AI 评分参与组合或策略侧的辅助判断。",
    increase_effect: "布尔开关没有调大含义；打开后会纳入 AI 评分。",
    decrease_effect: "布尔开关没有调小含义；关闭后只按规则信号运行。"
  }
];

export function ParameterForm({ parameters, values, onChange, onValidationChange }: Props) {
  const [draft, setDraft] = useState<Record<string, unknown>>(values);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const controls = useMemo(() => withExtraControls(parameters), [parameters]);

  useEffect(() => {
    setDraft(values);
    setErrors({});
    onValidationChange?.({});
  }, [values]);

  const update = (control: Control, value: unknown) => {
    const next = { ...draft, [control.name]: value };
    const nextErrors = validateControls(controls, next);
    setDraft(next);
    setErrors(nextErrors);
    onValidationChange?.(nextErrors);
    if (Object.keys(nextErrors).length === 0) {
      onChange(next);
    }
  };

  const sections = [
    { title: "选股条件", controls: controls.filter((control) => sectionFor(control.name) === "selection") },
    { title: "技术指标", controls: controls.filter((control) => sectionFor(control.name) === "indicator") },
    { title: "AI参与评分", controls: controls.filter((control) => sectionFor(control.name) === "ai") },
    { title: "交易设置", controls: controls.filter((control) => sectionFor(control.name) === "trading") }
  ];

  return (
    <div className="parameter-form">
      {sections.map((section) => (
        <details className="parameter-section" key={section.title} open>
          <summary>{section.title}</summary>
          <div className="parameter-grid">{section.controls.map((control) => renderControl(control, draft, errors, update))}</div>
        </details>
      ))}
    </div>
  );
}

export function validateStrategyParameterValues(parameters: StrategyParameter[], values: Record<string, unknown>): string[] {
  return withExtraControls(parameters).flatMap((control) => {
    const annotation = control.annotation.toLowerCase();
    const value = values[control.name] ?? control.default;
    if (typeof control.default === "number" || annotation.includes("int") || annotation.includes("float")) {
      if (value === "" || value === null || value === undefined || (typeof value === "number" && Number.isNaN(value))) {
        return [`${control.name} 不能为空`];
      }
      if (typeof value !== "number" || !Number.isFinite(value)) {
        return [`${control.name} 必须是有效数字`];
      }
    }
    return [];
  });
}

function withExtraControls(parameters: StrategyParameter[]): Control[] {
  const existing = new Set(parameters.map((parameter) => parameter.name));
  return [...parameters, ...EXTRA_CONTROLS.filter((control) => !existing.has(control.name))];
}

function sectionFor(name: string): "selection" | "indicator" | "ai" | "trading" {
  if (name === "symbol" || name.includes("stock") || name.includes("exchange")) return "selection";
  if (name.includes("ai_")) return "ai";
  if (name.includes("size") || name.includes("holding") || name.includes("stop") || name.includes("take") || name.includes("order")) return "trading";
  return "indicator";
}

function renderControl(
  control: Control,
  draft: Record<string, unknown>,
  errors: Record<string, string>,
  update: (control: Control, value: unknown) => void
) {
  const label = control.display_name ?? control.label ?? control.name;
  const value = draft[control.name] ?? control.default ?? "";
  const annotation = control.annotation.toLowerCase();
  const error = errors[control.name];

  if (control.options?.length && control.multiple) {
    const selected = selectedOptions(control, value);
    return (
      <div className="field" key={control.name}>
        <span className="field-label">{label}</span>
        <div className="multi-option-grid" role="group" aria-label={label}>
          {control.options.map((option) => (
            <label className="option-chip" key={option}>
              <input
                aria-label={`${label} ${option}`}
                type="checkbox"
                checked={selected.includes(option)}
                onChange={(event) => update(control, nextMultiValue(control, value, option, event.currentTarget.checked))}
              />
              <span>{option}</span>
            </label>
          ))}
        </div>
        {renderGuidance(control)}
      </div>
    );
  }

  if (control.options?.length) {
    return (
      <div className="field" key={control.name}>
        <label>
          <span>{label}</span>
          <select aria-label={label} value={String(value)} onChange={(event) => update(control, event.currentTarget.value)}>
            {control.options.map((option) => (
              <option key={option}>{option}</option>
            ))}
          </select>
        </label>
        {renderGuidance(control)}
      </div>
    );
  }

  if (typeof control.default === "boolean" || annotation.includes("bool")) {
    return (
      <div className="field" key={control.name}>
        <label className="field-toggle">
          <span>{label}</span>
          <input aria-label={label} type="checkbox" checked={Boolean(value)} onChange={(event) => update(control, event.currentTarget.checked)} />
        </label>
        {renderGuidance(control)}
      </div>
    );
  }

  if (typeof control.default === "number" || annotation.includes("int") || annotation.includes("float")) {
    return (
      <div className="field" key={control.name}>
        <label>
          <span>{label}</span>
          <input
            aria-label={label}
            aria-invalid={Boolean(error)}
            type="number"
            value={String(value)}
            onChange={(event) => {
              const raw = event.currentTarget.value;
              update(control, raw === "" ? "" : Number(raw));
            }}
          />
        </label>
        {error ? <small className="field-error">{error}</small> : null}
        {renderGuidance(control)}
      </div>
    );
  }

  return (
    <div className="field" key={control.name}>
      <label>
        <span>{label}</span>
        <input aria-label={label} value={String(value)} onChange={(event) => update(control, event.currentTarget.value)} />
      </label>
      {renderGuidance(control)}
    </div>
  );
}

function selectedOptions(control: Control, value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  const raw = String(value || control.default || "").trim();
  if (!raw) return control.options?.includes("all") ? ["all"] : [];
  return raw
    .split(",")
    .map((option) => option.trim())
    .filter((option) => option.length > 0);
}

function nextMultiValue(control: Control, currentValue: unknown, option: string, checked: boolean): string {
  const options = control.options ?? [];
  let selected = new Set(selectedOptions(control, currentValue));
  if (option === "all") {
    selected = checked ? new Set(["all"]) : new Set(options.includes("all") ? ["all"] : []);
  } else {
    selected.delete("all");
    if (checked) {
      selected.add(option);
    } else {
      selected.delete(option);
    }
    if (selected.size === 0 && options.includes("all")) {
      selected.add("all");
    }
  }
  return options.filter((candidate) => selected.has(candidate)).join(",");
}

function renderGuidance(control: Control) {
  if (!control.description && !control.increase_effect && !control.decrease_effect) return null;
  return (
    <div className="parameter-guidance">
      {control.description ? <p>{control.description}</p> : null}
      {control.increase_effect || control.decrease_effect ? (
        <div className="parameter-impact">
          {control.increase_effect ? <span>{`调大：${control.increase_effect}`}</span> : null}
          {control.decrease_effect ? <span>{`调小：${control.decrease_effect}`}</span> : null}
        </div>
      ) : null}
    </div>
  );
}

function validateControls(controls: Control[], values: Record<string, unknown>): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const control of controls) {
    if (!isNumericControl(control)) continue;
    const label = control.display_name ?? control.label ?? control.name;
    const value = values[control.name] ?? control.default ?? "";
    if (value === "") {
      errors[control.name] = `${label} 不能为空`;
      continue;
    }
    if (typeof value !== "number" || !Number.isFinite(value)) {
      errors[control.name] = `${label} 必须是数字`;
    }
  }
  return errors;
}

function isNumericControl(control: Control): boolean {
  const annotation = control.annotation.toLowerCase();
  return typeof control.default === "number" || annotation.includes("int") || annotation.includes("float");
}
