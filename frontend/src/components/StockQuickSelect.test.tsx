import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { StockQuickSelect } from "./StockQuickSelect";

test("StockQuickSelect selects a watchlist stock by exchange and code", async () => {
  const user = userEvent.setup();
  const onSelect = vi.fn();

  render(
    <StockQuickSelect
      label="全局自选股票"
      value={{ code: "000001", exchange: "SZSE" }}
      stocks={[
        { code: "000001", name: "平安银行", exchange: "SZSE" },
        { code: "601318", name: "中国平安", exchange: "SSE" }
      ]}
      onSelect={onSelect}
    />
  );

  await user.selectOptions(screen.getByLabelText("全局自选股票"), "SSE:601318");

  expect(onSelect).toHaveBeenCalledWith({ code: "601318", name: "中国平安", exchange: "SSE" });
});

test("StockQuickSelect shows an empty state when no watchlist stocks exist", () => {
  render(<StockQuickSelect label="全局自选股票" value={{ code: "000001", exchange: "SZSE" }} stocks={[]} onSelect={vi.fn()} />);

  expect(screen.getByLabelText("全局自选股票")).toBeDisabled();
  expect(screen.getByText("暂无自选股票")).toBeInTheDocument();
});
