import type { Stock } from "../types";

type Props = {
  label: string;
  value: { code?: string; symbol?: string; exchange: string };
  stocks: Stock[];
  onSelect: (stock: Stock) => void;
  compact?: boolean;
};

export function StockQuickSelect({ label, value, stocks, onSelect, compact = false }: Props) {
  const selectedKey = stockKey(value);
  return (
    <label className={compact ? "stock-quick-select compact" : "stock-quick-select"}>
      <span>{label}</span>
      <select
        aria-label={label}
        value={stocks.some((stock) => stockKey(stock) === selectedKey) ? selectedKey : ""}
        disabled={stocks.length === 0}
        onChange={(event) => {
          const stock = stocks.find((item) => stockKey(item) === event.currentTarget.value);
          if (stock) onSelect(stock);
        }}
      >
        {stocks.length === 0 ? (
          <option value="">暂无自选股票</option>
        ) : (
          <>
            <option value="">选择自选股票</option>
            {stocks.map((stock) => (
              <option key={stockKey(stock)} value={stockKey(stock)}>
                {stock.code} {stock.name} {stock.exchange}
              </option>
            ))}
          </>
        )}
      </select>
    </label>
  );
}

function stockKey(stock: { code?: string; symbol?: string; exchange: string }): string {
  return `${stock.exchange}:${stock.code ?? stock.symbol ?? ""}`;
}
