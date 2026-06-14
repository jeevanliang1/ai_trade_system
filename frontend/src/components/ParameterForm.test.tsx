import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ParameterForm } from "./ParameterForm";
import type { StrategyParameter } from "../types";

test("renders typed strategy parameters and reports changes", async () => {
  const user = userEvent.setup();
  const changes: Record<string, unknown>[] = [];
  const parameters: StrategyParameter[] = [
    { name: "symbol", annotation: "str", default: "000001" },
    { name: "fast", annotation: "int", default: 5 },
    { name: "enabled", annotation: "bool", default: true }
  ];

  render(<ParameterForm parameters={parameters} values={{}} onChange={(next) => changes.push(next)} />);

  await user.clear(screen.getByLabelText("fast"));
  await user.type(screen.getByLabelText("fast"), "8");

  expect(changes.at(-1)).toMatchObject({ fast: 8 });
  expect(screen.getByLabelText("enabled")).toBeChecked();
});

test("rejects empty numeric values before publishing parameter changes", async () => {
  const user = userEvent.setup();
  const changes: Record<string, unknown>[] = [];
  const validationStates: Record<string, string>[] = [];
  const parameters: StrategyParameter[] = [{ name: "fast", annotation: "int", default: 5 }];

  render(
    <ParameterForm
      parameters={parameters}
      values={{ fast: 5 }}
      onChange={(next) => changes.push(next)}
      onValidationChange={(errors) => validationStates.push(errors)}
    />
  );

  await user.clear(screen.getByLabelText("fast"));

  expect(screen.getByText("fast 不能为空")).toBeInTheDocument();
  expect(changes).toEqual([]);
  expect(validationStates.at(-1)).toEqual({ fast: "fast 不能为空" });

  await user.type(screen.getByLabelText("fast"), "8");

  expect(changes.at(-1)).toMatchObject({ fast: 8 });
  expect(validationStates.at(-1)).toEqual({});
});

test("groups screenshot strategy controls into collapsible sections", async () => {
  const user = userEvent.setup();
  const changes: Record<string, unknown>[] = [];
  const parameters: StrategyParameter[] = [
    { name: "symbol", annotation: "str", default: "000001" },
    { name: "fast", annotation: "int", default: 5 },
    { name: "slow", annotation: "int", default: 20 },
    { name: "size", annotation: "int", default: 100 }
  ];

  render(<ParameterForm parameters={parameters} values={{}} onChange={(next) => changes.push(next)} />);

  expect(screen.getByText("选股条件")).toBeInTheDocument();
  expect(screen.getByText("技术指标")).toBeInTheDocument();
  expect(screen.getByText("AI参与评分")).toBeInTheDocument();
  expect(screen.getByText("交易设置")).toBeInTheDocument();

  await user.selectOptions(screen.getByLabelText("MA类型"), "EMA");
  await user.clear(screen.getByLabelText("AI评分阈值"));
  await user.type(screen.getByLabelText("AI评分阈值"), "72");
  await user.click(screen.getByLabelText("启用AI评分"));

  expect(changes.at(-1)).toMatchObject({ ma_type: "EMA", ai_score_threshold: 72, ai_enabled: true });
});
