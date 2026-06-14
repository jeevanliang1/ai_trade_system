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
