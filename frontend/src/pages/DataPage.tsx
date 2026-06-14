import { AlertTriangle, Download, FileDown, RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { formatRequestError } from "../api/errors";
import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { ToolbarButton } from "../components/ToolbarButton";
import type { Bar, PlatformSettings, Stock } from "../types";
import { priceOption } from "./chartOptions";
import type { PageProps } from "./pageTypes";

export function DataPage({ state, actions }: PageProps) {
  const [stockQuery, setStockQuery] = useState("");
  const [stockResults, setStockResults] = useState<Stock[]>([]);
  const [stockSearchStatus, setStockSearchStatus] = useState<"idle" | "loading" | "error">("idle");
  const [stockSearchMessage, setStockSearchMessage] = useState("");

  const update = (key: keyof typeof state.settings, value: string | number) => {
    actions.setSettings({ ...state.settings, [key]: value });
  };
  const validationErrors = useMemo(() => validateDataSettings(state.settings), [state.settings]);
  const hasErrors = validationErrors.length > 0;
  const isErrorState = state.message.startsWith("请求失败");
  const health = useMemo(() => buildDataHealth(state.bars, state.settings, state.dataSummary), [state.bars, state.settings, state.dataSummary]);

  useEffect(() => {
    const query = stockQuery.trim();
    if (!query) {
      setStockResults([]);
      setStockSearchStatus("idle");
      setStockSearchMessage("");
      return;
    }
    let cancelled = false;
    setStockSearchStatus("loading");
    setStockSearchMessage("");
    void api
      .stocks(query, 8)
      .then((stocks) => {
        if (cancelled) return;
        setStockResults(stocks);
        setStockSearchStatus("idle");
        setStockSearchMessage("");
      })
      .catch((error) => {
        if (cancelled) return;
        setStockResults([]);
        setStockSearchStatus("error");
        setStockSearchMessage(`股票搜索失败：${formatRequestError(error)}`);
      });
    return () => {
      cancelled = true;
    };
  }, [stockQuery]);

  const selectStock = (stock: Stock) => {
    actions.setSettings({
      ...state.settings,
      symbol: stock.code,
      exchange: stock.exchange,
      csv_path: `data/${stock.code}_daily.csv`
    });
    setStockQuery(`${stock.code} ${stock.name}`);
    setStockResults([]);
  };

  const runWhenValid = (task: () => Promise<void>) => {
    if (hasErrors || state.busy) return;
    void task();
  };

  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">数据中心工作区</div>
        <label className="field">
          <span>搜索股票名称或代码</span>
          <div className="search-box">
            <Search size={14} />
            <input value={stockQuery} onChange={(event) => setStockQuery(event.currentTarget.value)} placeholder="例如：中国平安 / 601318" />
          </div>
        </label>
        {(stockResults.length > 0 || stockSearchStatus !== "idle") && (
          <div className="stock-results" aria-label="股票搜索结果">
            {stockSearchStatus === "loading" && <div className="stock-result-note">搜索中...</div>}
            {stockSearchStatus === "error" && <div className="stock-result-note negative">{stockSearchMessage || "股票搜索失败"}</div>}
            {stockSearchStatus === "idle" &&
              stockResults.map((stock) => (
                <button
                  key={`${stock.exchange}:${stock.code}`}
                  type="button"
                  aria-label={`${stock.code} ${stock.name} ${stock.exchange}`}
                  onClick={() => selectStock(stock)}
                >
                  <strong>{stock.code}</strong>
                  <span>{stock.name}</span>
                  <small>{stock.exchange}</small>
                </button>
              ))}
          </div>
        )}
        <label className="field">
          <span>股票代码</span>
          <input value={state.settings.symbol} onChange={(event) => update("symbol", event.currentTarget.value)} />
        </label>
        <label className="field">
          <span>交易所</span>
          <select value={state.settings.exchange} onChange={(event) => update("exchange", event.currentTarget.value)}>
            <option>SZSE</option>
            <option>SSE</option>
            <option>BSE</option>
          </select>
        </label>
        <label className="field">
          <span>开始日期</span>
          <input value={state.settings.start_date} onChange={(event) => update("start_date", event.currentTarget.value)} />
        </label>
        <label className="field">
          <span>结束日期</span>
          <input value={state.settings.end_date} onChange={(event) => update("end_date", event.currentTarget.value)} />
        </label>
        <label className="field">
          <span>CSV路径</span>
          <input value={state.settings.csv_path} onChange={(event) => update("csv_path", event.currentTarget.value)} />
        </label>
        {validationErrors.length > 0 && (
          <div className="form-errors" role="alert">
            {validationErrors.map((error) => (
              <span key={error}>{error}</span>
            ))}
          </div>
        )}
        <div className="button-row">
          <ToolbarButton icon={<RefreshCw size={16} />} disabled={hasErrors || state.busy} onClick={() => runWhenValid(actions.loadData)}>
            加载CSV
          </ToolbarButton>
          <ToolbarButton icon={<FileDown size={16} />} variant="primary" disabled={hasErrors || state.busy} onClick={() => runWhenValid(actions.demoData)}>
            生成演示数据
          </ToolbarButton>
          <ToolbarButton icon={<Download size={16} />} disabled={hasErrors || state.busy} onClick={() => runWhenValid(actions.downloadData)}>
            下载日线数据
          </ToolbarButton>
        </div>
        {state.busy && <div className="data-status">正在处理数据请求...</div>}
        {isErrorState && (
          <div className="data-error" role="alert">
            <AlertTriangle size={16} />
            <div>
              <strong>{state.message}</strong>
              <span>重试下载，或生成演示数据继续验证后续流程。</span>
            </div>
            <button type="button" onClick={() => runWhenValid(actions.downloadData)} disabled={hasErrors || state.busy}>
              重试下载
            </button>
          </div>
        )}
      </section>
      <section className="main-column">
        <MetricStrip
          metrics={[
            { label: "K线数量", value: state.bars.length },
            { label: "最新收盘", value: state.bars.at(-1)?.close_price.toFixed(2) ?? "-" },
            { label: "成交量", value: state.bars.at(-1)?.volume.toLocaleString() ?? "-" },
            { label: "成交额", value: state.bars.at(-1)?.turnover.toLocaleString() ?? "-" }
          ]}
        />
        <section className="panel">
          <div className="panel-title">数据健康</div>
          <div className="data-health-grid">
            <HealthItem label="行数" value={`${health.rows} 行`} />
            <HealthItem label="覆盖区间" value={health.coverage} />
            <HealthItem label="缺失值" value={`${health.missingValues} 处`} tone={health.missingValues > 0 ? "warning" : "ok"} />
            <HealthItem label="最新收盘" value={formatOptionalNumber(health.latestClose, 2)} />
            <HealthItem label="本地路径" value={health.csvPath} />
            <HealthItem label="路径状态" value={health.pathStatus} tone={health.pathStatus === "可用路径" ? "ok" : "warning"} />
          </div>
        </section>
        <ChartPanel title="价格走势" option={priceOption(state.bars)} height={360} />
        <section className="panel">
          <div className="panel-title">行情预览</div>
          <DataTable rows={state.bars.slice(-80).reverse() as unknown as Record<string, unknown>[]} />
        </section>
      </section>
    </div>
  );
}

function HealthItem({ label, value, tone = "neutral" }: { label: string; value: string | number; tone?: "neutral" | "ok" | "warning" }) {
  return (
    <div className={`data-health-item ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function validateDataSettings(settings: PlatformSettings): string[] {
  const errors: string[] = [];
  if (!settings.csv_path.trim()) {
    errors.push("CSV路径不能为空");
  }
  if (!isDateKey(settings.start_date) || !isDateKey(settings.end_date)) {
    errors.push("日期格式需为 YYYYMMDD");
  } else if (settings.start_date > settings.end_date) {
    errors.push("开始日期不能晚于结束日期");
  }
  return errors;
}

function isDateKey(value: string): boolean {
  return /^\d{8}$/.test(value);
}

function buildDataHealth(bars: Bar[], settings: PlatformSettings, summary: PageProps["state"]["dataSummary"]) {
  const firstBar = bars[0];
  const lastBar = bars.at(-1);
  const start = summary?.start ?? firstBar?.trading_day ?? null;
  const end = summary?.end ?? lastBar?.trading_day ?? null;
  const csvPath = settings.csv_path;
  const loadedPath = summary?.csv_path ?? settings.csv_path;
  const pathLooksValid = csvPath.trim().startsWith("data/") && csvPath.trim().endsWith(".csv");
  return {
    rows: summary?.rows ?? bars.length,
    coverage: start && end ? `${start} 至 ${end}` : "-",
    missingValues: countMissingValues(bars),
    latestClose: summary?.latest_close ?? lastBar?.close_price ?? null,
    csvPath,
    pathStatus: loadedPath !== csvPath ? "待加载新路径" : pathLooksValid ? "可用路径" : "待检查路径"
  };
}

function countMissingValues(bars: Bar[]): number {
  const fields: (keyof Bar)[] = ["open_price", "high_price", "low_price", "close_price", "volume", "turnover"];
  let count = 0;
  for (const bar of bars) {
    for (const field of fields) {
      const value = bar[field];
      if (value == null || (typeof value === "number" && Number.isNaN(value))) {
        count += 1;
      }
    }
  }
  return count;
}

function formatOptionalNumber(value: number | null, digits = 0): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
