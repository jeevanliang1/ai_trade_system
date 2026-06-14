import { useEffect, useState } from "react";

import type { StrategyParameter } from "../types";

type Props = {
  parameters: StrategyParameter[];
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
};

export function ParameterForm({ parameters, values, onChange }: Props) {
  const [draft, setDraft] = useState<Record<string, unknown>>(values);

  useEffect(() => {
    setDraft(values);
  }, [values]);

  const update = (name: string, value: unknown) => {
    const next = { ...draft, [name]: value };
    setDraft(next);
    onChange(next);
  };

  return (
    <div className="parameter-form">
      {parameters.map((parameter) => {
        const value = draft[parameter.name] ?? parameter.default ?? "";
        const annotation = parameter.annotation.toLowerCase();
        if (typeof parameter.default === "boolean" || annotation.includes("bool")) {
          return (
            <label className="field row-field" key={parameter.name}>
              <span>{parameter.name}</span>
              <input
                aria-label={parameter.name}
                type="checkbox"
                checked={Boolean(value)}
                onChange={(event) => update(parameter.name, event.currentTarget.checked)}
              />
            </label>
          );
        }
        if (typeof parameter.default === "number" || annotation.includes("int") || annotation.includes("float")) {
          return (
            <label className="field" key={parameter.name}>
              <span>{parameter.name}</span>
              <input
                aria-label={parameter.name}
                type="number"
                value={String(value)}
                onChange={(event) => {
                  const raw = event.currentTarget.value;
                  update(parameter.name, raw === "" ? "" : Number(raw));
                }}
              />
            </label>
          );
        }
        return (
          <label className="field" key={parameter.name}>
            <span>{parameter.name}</span>
            <input aria-label={parameter.name} value={String(value)} onChange={(event) => update(parameter.name, event.currentTarget.value)} />
          </label>
        );
      })}
    </div>
  );
}
