import { Search, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { Stock } from "../types";

type Props = {
  label: string;
  value: { code?: string; symbol?: string; exchange: string };
  stocks: Stock[];
  onSelect: (stock: Stock) => void;
  onSearch: (query: string, limit?: number) => Promise<Stock[]>;
  compact?: boolean;
};

export function StockQuickSelect({ label, value, stocks, onSelect, onSearch, compact = false }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Stock[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const selectedKey = stockKey(value);
  const selected = useMemo(() => stocks.find((stock) => stockKey(stock) === selectedKey), [selectedKey, stocks]);
  const visibleStocks = query.trim() ? results : stocks;
  const sectionTitle = query.trim() ? "推荐索引" : "我的自选";

  useEffect(() => {
    if (!open) return;
    const keyword = query.trim();
    if (!keyword) {
      setResults([]);
      setStatus("idle");
      return;
    }
    let cancelled = false;
    setStatus("loading");
    void onSearch(keyword, 12)
      .then((items) => {
        if (cancelled) return;
        setResults(items);
        setStatus("idle");
      })
      .catch(() => {
        if (cancelled) return;
        setResults([]);
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [open, onSearch, query]);

  const chooseStock = (stock: Stock) => {
    onSelect(stock);
    setOpen(false);
    setQuery("");
  };

  return (
    <div className={compact ? "stock-quick-select compact" : "stock-quick-select"}>
      <span>{label}</span>
      <button type="button" className="stock-picker-trigger" onClick={() => setOpen(true)} aria-haspopup="dialog">
        {label} {selected ? stockLabel(selected) : "选择股票"}
      </button>
      {open ? (
        <div className="modal-backdrop" role="presentation">
          <section className="stock-picker-dialog" role="dialog" aria-modal="true" aria-label={label}>
            <header>
              <strong>{label}</strong>
              <button type="button" className="icon-button" aria-label="关闭股票选择" onClick={() => setOpen(false)}>
                <X size={16} />
              </button>
            </header>
            <label className="stock-picker-search">
              <Search size={15} />
              <input
                aria-label="搜索股票名称或代码"
                value={query}
                placeholder="搜索 A股 / 美股 / 数字货币"
                autoFocus
                onChange={(event) => setQuery(event.currentTarget.value)}
              />
            </label>
            <div className="stock-picker-section-title">
              <span>{sectionTitle}</span>
              <small>{visibleStocks.length} 个匹配</small>
            </div>
            <div className="stock-picker-list">
              {status === "loading" ? <div className="stock-picker-note">搜索中...</div> : null}
              {status === "error" ? <div className="stock-picker-note negative">搜索失败，请稍后重试</div> : null}
              {status === "idle" && visibleStocks.length === 0 ? <div className="stock-picker-note">暂无匹配股票</div> : null}
              {status === "idle"
                ? visibleStocks.map((stock) => (
                    <button
                      key={stockKey(stock)}
                      type="button"
                      className={stockKey(stock) === selectedKey ? "active" : ""}
                      aria-label={`选择 ${stockLabel(stock)}`}
                      onClick={() => chooseStock(stock)}
                    >
                      <strong>{stock.code}</strong>
                      <span>{stock.name}</span>
                      <small>{stock.exchange}</small>
                    </button>
                  ))
                : null}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function stockKey(stock: { code?: string; symbol?: string; exchange: string }): string {
  return `${stock.exchange}:${stock.code ?? stock.symbol ?? ""}`;
}

function stockLabel(stock: Stock): string {
  return `${stock.code} ${stock.name} ${stock.exchange}`;
}
