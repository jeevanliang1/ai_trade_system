import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AppShell, NAV_ITEMS } from "./AppShell";

test("renders screenshot-inspired navigation and switches pages", async () => {
  const user = userEvent.setup();
  render(<AppShell />);

  expect(screen.getByText("AI量化平台")).toBeInTheDocument();
  expect(screen.getByText("准备")).toBeInTheDocument();
  expect(screen.getByText("股票配置")).toBeInTheDocument();
  expect(screen.getByText("策略")).toBeInTheDocument();
  expect(screen.getByText("验证")).toBeInTheDocument();
  expect(screen.getByText("辅助")).toBeInTheDocument();
  expect(screen.getByText("策略工坊")).toHaveClass("active");
  expect(screen.queryByRole("button", { name: "运行回测" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "去回测中心" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "新建策略" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "保存" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "另存为" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "停止" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "回测设置" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "导出报告" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "收起" })).not.toBeInTheDocument();
  expect(screen.getByText("路径：data/000001_daily.csv")).toBeInTheDocument();
  expect(screen.getByText("周期：daily")).toBeInTheDocument();
  expect(screen.getByText("滑点：0.01")).toBeInTheDocument();
  expect(NAV_ITEMS).toHaveLength(14);
  expect(NAV_ITEMS.map((item) => item.id)).toContain("agent");
  expect(NAV_ITEMS.map((item) => item.id)).toContain("agent-governance");
  expect(NAV_ITEMS.map((item) => item.id)).toContain("automation");
  expect(NAV_ITEMS.map((item) => item.id)).toContain("realtime");

  await user.click(screen.getByRole("button", { name: "去回测中心" }));
  expect(screen.getByText("回测中心")).toHaveClass("active");
  expect(screen.getByText("回测设置")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "数据中心" }));

  expect(screen.getByText("数据中心")).toHaveClass("active");
  expect(screen.getByText("下载日线数据")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "信号雷达" }));
  expect(screen.getByRole("button", { name: "信号雷达" })).toHaveClass("active");
  expect(screen.getByRole("button", { name: "批量扫描" })).toBeInTheDocument();
});
