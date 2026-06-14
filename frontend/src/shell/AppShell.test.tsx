import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AppShell, NAV_ITEMS } from "./AppShell";

test("renders screenshot-inspired navigation and switches pages", async () => {
  const user = userEvent.setup();
  render(<AppShell />);

  expect(screen.getByText("AI量化平台")).toBeInTheDocument();
  expect(screen.getByText("策略工坊")).toHaveClass("active");
  expect(screen.getByText("运行回测")).toBeInTheDocument();
  expect(NAV_ITEMS).toHaveLength(8);

  await user.click(screen.getByRole("button", { name: "数据中心" }));

  expect(screen.getByText("数据中心")).toHaveClass("active");
  expect(screen.getByText("下载日线数据")).toBeInTheDocument();
});
