import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { StockQuickSelect } from "./StockQuickSelect";

test("StockQuickSelect selects a watchlist stock by exchange and code", async () => {
  const user = userEvent.setup();
  const onSelect = vi.fn();
  const onSearch = vi.fn().mockResolvedValue([
    { code: "601318", name: "中国平安", exchange: "SSE" },
    { code: "AAPL", name: "Apple", exchange: "NASDAQ" },
    { code: "BTCUSDT", name: "Bitcoin", exchange: "CRYPTO" }
  ]);

  render(
    <StockQuickSelect
      label="全局自选股票"
      value={{ code: "000001", exchange: "SZSE" }}
      stocks={[
        { code: "000001", name: "平安银行", exchange: "SZSE" },
        { code: "601318", name: "中国平安", exchange: "SSE" }
      ]}
      onSelect={onSelect}
      onSearch={onSearch}
    />
  );

  await user.click(screen.getByRole("button", { name: "全局自选股票 000001 平安银行 SZSE" }));
  expect(screen.getByRole("dialog", { name: "全局自选股票" })).toBeInTheDocument();
  expect(screen.getByText("我的自选")).toBeInTheDocument();

  await user.type(screen.getByLabelText("搜索股票名称或代码"), "btc");
  expect(onSearch).toHaveBeenCalledWith("btc", 12);
  await user.click(await screen.findByRole("button", { name: "选择 BTCUSDT Bitcoin CRYPTO" }));

  expect(onSelect).toHaveBeenCalledWith({ code: "BTCUSDT", name: "Bitcoin", exchange: "CRYPTO" });
});

test("StockQuickSelect shows an empty state when no watchlist stocks exist", () => {
  render(<StockQuickSelect label="全局自选股票" value={{ code: "", exchange: "" }} stocks={[]} onSelect={vi.fn()} onSearch={vi.fn()} />);

  expect(screen.getByRole("button", { name: "全局自选股票 选择股票" })).toBeEnabled();
});
