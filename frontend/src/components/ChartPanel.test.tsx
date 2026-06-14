import { render, screen } from "@testing-library/react";

import { ChartPanel } from "./ChartPanel";

test("ChartPanel exposes chart group for linked zoom panels", () => {
  render(<ChartPanel title="成交量" option={{ series: [] }} group="strategy-workshop-price-volume" />);

  expect(screen.getByLabelText("成交量 图表")).toHaveAttribute("data-chart-group", "strategy-workshop-price-volume");
});
