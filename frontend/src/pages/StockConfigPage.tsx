import { CheckCircle2, Database, RefreshCw, Search, Star, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api/client";
import { formatRequestError } from "../api/errors";
import { ToolbarButton } from "../components/ToolbarButton";
import type { Stock } from "../types";
import type { PageProps } from "./pageTypes";

export function StockConfigPage({ state, actions }: PageProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Stock[]>([]);
  const [searchStatus, setSearchStatus] = useState<"idle" | "loading" | "error">("idle");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const keyword = query.trim();
    if (!keyword) {
      setResults([]);
      setSearchStatus("idle");
      setMessage("");
      return;
    }
    let cancelled = false;
    setSearchStatus("loading");
    setMessage("");
    void api
      .stocks(keyword, 10)
      .then((stocks) => {
        if (cancelled) return;
        setResults(stocks);
        setSearchStatus("idle");
      })
      .catch((error) => {
        if (cancelled) return;
        setResults([]);
        setSearchStatus("error");
        setMessage(`股票搜索失败：${formatRequestError(error)}`);
      });
    return () => {
      cancelled = true;
    };
  }, [query]);

  const addStock = async (stock: Stock) => {
    const next = mergeWatchlist(state.watchlist, stock);
    const saved = await persistWatchlist(next, actions.setWatchlist, setMessage);
    if (saved) {
      await actions.updateWatchlistData(fiveYearMaintenanceRequest(state.settings));
    }
  };

  const removeStock = async (stock: Stock) => {
    const next = state.watchlist.filter((item) => stockKey(item) !== stockKey(stock));
    await persistWatchlist(next, actions.setWatchlist, setMessage);
  };

  return (
    <div className="page-grid stock-config-page">
      <section className="panel side-panel">
        <div className="panel-title between">
          <span>股票配置中心</span>
          <Star size={16} />
        </div>
        <label className="field">
          <span>搜索股票加入自选</span>
          <div className="search-box">
            <Search size={14} />
            <input aria-label="搜索股票加入自选" value={query} placeholder="输入股票名称或代码" onChange={(event) => setQuery(event.currentTarget.value)} />
          </div>
        </label>
        {(results.length > 0 || searchStatus !== "idle") && (
          <div className="stock-results" aria-label="股票搜索结果">
            {searchStatus === "loading" ? <div className="stock-result-note">搜索中...</div> : null}
            {searchStatus === "error" ? <div className="stock-result-note negative">{message || "股票搜索失败"}</div> : null}
            {searchStatus === "idle"
              ? results.map((stock) => (
                  <button key={stockKey(stock)} type="button" aria-label={`添加 ${stock.code} ${stock.name} ${stock.exchange}`} onClick={() => void addStock(stock)}>
                    <strong>{stock.code}</strong>
                    <span>{stock.name}</span>
                    <small>{stock.exchange}</small>
                  </button>
                ))
              : null}
          </div>
        )}
        {message ? <p className={message.startsWith("自选股保存失败") || message.startsWith("股票搜索失败") ? "inline-alert" : "inline-success"}>{message}</p> : null}
      </section>

      <main className="main-column">
        <section className="panel">
          <div className="panel-title between">
            <span>我的自选股票</span>
            <div className="panel-title-actions">
              <small>{state.watchlist.length} 只</small>
              <ToolbarButton icon={<RefreshCw size={14} />} onClick={() => void actions.updateWatchlistData()}>
                更新全部自选股数据
              </ToolbarButton>
            </div>
          </div>
          {state.watchlist.length ? (
            <div className="watchlist-grid">
              {state.watchlist.map((stock) => {
                const status = dataStatusFor(stock, state.managedData, state.settings.timeframe);
                return (
                  <article className={stockKey(stock) === stockKey(state.settings) ? "watchlist-card active" : "watchlist-card"} key={stockKey(stock)}>
                    <header>
                      <strong>{stock.code}</strong>
                      <span>{stock.exchange}</span>
                    </header>
                    <b>{stock.name}</b>
                    <div className={status?.exists && !status.stale ? "watchlist-data-status ok" : "watchlist-data-status"}>
                      <Database size={14} />
                      <div>
                        <strong>{dataStatusLabel(status)}</strong>
                        <span>{status?.latest_rows ?? 0} 行 · {status?.timeframe ?? state.settings.timeframe}</span>
                        <small>{status?.latest_path ?? managedCsvPath(stock, state.settings.timeframe)}</small>
                      </div>
                    </div>
                    <div className="watchlist-actions">
                      <ToolbarButton icon={<CheckCircle2 size={14} />} onClick={() => actions.selectStock(stock)}>
                        设为当前 {stock.code} {stock.name}
                      </ToolbarButton>
                      <button className="icon-button danger" type="button" aria-label={`移除 ${stock.code} ${stock.name}`} onClick={() => void removeStock(stock)}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="empty-table">暂无自选股票，先从左侧搜索并加入。</div>
          )}
        </section>
      </main>
    </div>
  );
}

async function persistWatchlist(stocks: Stock[], setWatchlist: (stocks: Stock[]) => void, setMessage: (message: string) => void): Promise<boolean> {
  try {
    const payload = await api.saveWatchlist(stocks);
    setWatchlist(payload.stocks);
    setMessage("自选股已保存");
    return true;
  } catch (error) {
    setMessage(`自选股保存失败：${formatRequestError(error)}`);
    return false;
  }
}

function mergeWatchlist(stocks: Stock[], stock: Stock): Stock[] {
  if (stocks.some((item) => stockKey(item) === stockKey(stock))) return stocks;
  return [...stocks, stock];
}

function stockKey(stock: { code?: string; symbol?: string; exchange: string }): string {
  return `${stock.exchange}:${stock.code ?? stock.symbol ?? ""}`;
}

function dataStatusFor(stock: Stock, files: PageProps["state"]["managedData"], timeframe: string) {
  return files.find((file) => file.code === stock.code && file.exchange === stock.exchange && file.timeframe === timeframe);
}

function dataStatusLabel(status: ReturnType<typeof dataStatusFor>): string {
  if (!status?.exists) return "未下载本地数据";
  if (status.stale && status.latest_end) return `需更新，最新至 ${status.latest_end}`;
  if (status.latest_end) return `数据已更新至 ${status.latest_end}`;
  return "本地数据状态未知";
}

function managedCsvPath(stock: Stock, timeframe: string): string {
  const market = stock.exchange === "CRYPTO" ? "crypto" : ["NASDAQ", "NYSE", "AMEX", "US"].includes(stock.exchange) ? "us_stock" : "a_share";
  return `data/market/${market}/${stock.exchange}/${stock.code}/${stock.code}_${stock.exchange}_${timeframe || "daily"}_qfq_latest.csv`;
}

function fiveYearMaintenanceRequest(settings: PageProps["state"]["settings"]) {
  const endDate = settings.end_date;
  return {
    start_date: shiftDateYears(endDate, -5),
    end_date: endDate,
    adjust: settings.adjust,
    timeframe: settings.timeframe,
    if_stale: true
  };
}

function shiftDateYears(dateKey: string, years: number): string {
  const year = Number(dateKey.slice(0, 4));
  const month = dateKey.slice(4, 6);
  const day = dateKey.slice(6, 8);
  if (!Number.isFinite(year) || month.length !== 2 || day.length !== 2) return dateKey;
  return `${year + years}${month}${day}`;
}
