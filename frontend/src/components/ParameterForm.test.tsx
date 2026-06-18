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


test("renders metadata-backed single-select strategy parameters", async () => {
  const user = userEvent.setup();
  const changes: Record<string, unknown>[] = [];
  const parameters: StrategyParameter[] = [
    {
      name: "signal_mode",
      annotation: "str",
      default: "all",
      display_name: "信号模式",
      options: ["all", "confirmation", "structure"]
    }
  ];

  render(<ParameterForm parameters={parameters} values={{ signal_mode: "all" }} onChange={(next) => changes.push(next)} />);

  await user.selectOptions(screen.getByLabelText("信号模式"), "confirmation");

  expect(changes.at(-1)).toMatchObject({ signal_mode: "confirmation" });
});


test("renders metadata-backed multi-select strategy parameters as comma strings", async () => {
  const user = userEvent.setup();
  const changes: Record<string, unknown>[] = [];
  const parameters: StrategyParameter[] = [
    {
      name: "allowed_point_types",
      annotation: "str",
      default: "all",
      display_name: "买卖点类型过滤",
      options: ["all", "first-buy", "second-buy", "third-buy"],
      multiple: true
    }
  ];

  render(
    <ParameterForm
      parameters={parameters}
      values={{ allowed_point_types: "all" }}
      onChange={(next) => changes.push(next)}
    />
  );

  await user.click(screen.getByLabelText("买卖点类型过滤 second-buy"));
  await user.click(screen.getByLabelText("买卖点类型过滤 third-buy"));

  expect(changes.at(-1)).toMatchObject({ allowed_point_types: "second-buy,third-buy" });
  expect(screen.getByLabelText("买卖点类型过滤 all")).not.toBeChecked();
  expect(screen.getByLabelText("买卖点类型过滤 second-buy")).toBeChecked();
  expect(screen.getByLabelText("买卖点类型过滤 third-buy")).toBeChecked();

  await user.click(screen.getByLabelText("买卖点类型过滤 all"));

  expect(changes.at(-1)).toMatchObject({ allowed_point_types: "all" });
  expect(screen.getByLabelText("买卖点类型过滤 all")).toBeChecked();
  expect(screen.getByLabelText("买卖点类型过滤 second-buy")).not.toBeChecked();
  expect(screen.getByLabelText("买卖点类型过滤 third-buy")).not.toBeChecked();
});

test("renders Chinese parameter guidance and tuning impact", () => {
  const parameters = [
    {
      name: "fast_window",
      annotation: "int",
      default: 5,
      display_name: "快线周期",
      description: "用于计算短期均线，决定策略观察短线价格变化的长度。",
      increase_effect: "调大后均线更平滑，信号更少更慢。",
      decrease_effect: "调小后均线更敏感，信号更多但噪音也更多。"
    }
  ];

  render(<ParameterForm parameters={parameters} values={{ fast_window: 5 }} onChange={vi.fn()} />);

  expect(screen.getByLabelText("快线周期")).toBeInTheDocument();
  expect(screen.getByText("用于计算短期均线，决定策略观察短线价格变化的长度。")).toBeInTheDocument();
  expect(screen.getByText("调大：调大后均线更平滑，信号更少更慢。")).toBeInTheDocument();
  expect(screen.getByText("调小：调小后均线更敏感，信号更多但噪音也更多。")).toBeInTheDocument();
});
