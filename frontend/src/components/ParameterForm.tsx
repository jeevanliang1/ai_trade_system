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
  { name: "rsi_period", label: "RSI周期", annotation: "int", default: 14 },
  { name: "rsi_lower", label: "RSI下限", annotation: "float", default: 30 },
  { name: "rsi_upper", label: "RSI上限", annotation: "float", default: 70 },
  { name: "ma_type", label: "MA类型", annotation: "select", default: "SMA", options: ["SMA", "EMA", "WMA"] },
  { name: "holding_period", label: "持仓周期", annotation: "int", default: 20 },
  { name: "stop_loss_pct", label: "止损比例", annotation: "float", default: 8 },
  { name: "take_profit_pct", label: "止盈比例", annotation: "float", default: 18 },
  { name: "max_order_size", label: "最大下单量", annotation: "int", default: 1000 },
  { name: "ai_score_threshold", label: "AI评分阈值", annotation: "float", default: 65 },
  { name: "ai_enabled", label: "启用AI评分", annotation: "bool", default: false }
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
  const label = control.label ?? control.name;
  const value = draft[control.name] ?? control.default ?? "";
  const annotation = control.annotation.toLowerCase();
  const error = errors[control.name];

  if (control.options?.length) {
    return (
      <label className="field" key={control.name}>
        <span>{label}</span>
        <select aria-label={label} value={String(value)} onChange={(event) => update(control, event.currentTarget.value)}>
          {control.options.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
      </label>
    );
  }

  if (typeof control.default === "boolean" || annotation.includes("bool")) {
    return (
      <label className="field row-field" key={control.name}>
        <span>{label}</span>
        <input aria-label={label} type="checkbox" checked={Boolean(value)} onChange={(event) => update(control, event.currentTarget.checked)} />
      </label>
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
      </div>
    );
  }

  return (
    <label className="field" key={control.name}>
      <span>{label}</span>
      <input aria-label={label} value={String(value)} onChange={(event) => update(control, event.currentTarget.value)} />
    </label>
  );
}

function validateControls(controls: Control[], values: Record<string, unknown>): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const control of controls) {
    if (!isNumericControl(control)) continue;
    const label = control.label ?? control.name;
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
