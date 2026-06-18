import { useMemo, useState } from "react";
import { Activity, AlertTriangle, Database, Download, Radar, Search } from "lucide-react";

import { api } from "../api/client";
import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { ToolbarButton } from "../components/ToolbarButton";
import type { PageProps } from "./pageTypes";
import type { ResearchSignalBatchResponse, ResearchSignalBatchRow, ResearchSignalBatchScoreMode } from "../types";

const DEFAULT_LIMIT = 20;
const DEFAULT_MIN_BARS = 60;
const DEFAULT_LOOKBACK = 120;
type ScanUniverse = "catalog" | "local_csv" | "current";
type ScanHistoryEntry = {
  id: number;
  query: string;
  universe: string;
  scoreMode: string;
  available: number;
  missing: number;
  scanned: number;
};

export function SignalRadarPage({ state, actions }: PageProps) {
  const [query, setQuery] = useState("");
  const [universe, setUniverse] = useState<ScanUniverse>("catalog");
  const [scoreMode, setScoreMode] = useState<ResearchSignalBatchScoreMode>("research");
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const [minBars, setMinBars] = useState(DEFAULT_MIN_BARS);
  const [lookback, setLookback] = useState(DEFAULT_LOOKBACK);
  const [result, setResult] = useState<ResearchSignalBatchResponse | null>(null);
  const [history, setHistory] = useState<ScanHistoryEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const rankedRows = useMemo(() => radarTableRows(result?.rows ?? []), [result]);
  const csvHref = useMemo(() => (result ? `data:text/csv;charset=utf-8,${encodeURIComponent(radarCsv(result))}` : ""), [result]);

  const runScan = async () => {
    setBusy(true);
    setError("");
    try {
      const payload = await api.batchResearchSignals(state.settings, { query: query.trim(), limit, min_bars: minBars, lookback, universe, score_mode: scoreMode });
      setResult(payload);
      setHistory((items) =>
        [
          {
            id: Date.now(),
            query: payload.query || "全部候选",
            universe: payload.universe,
            scoreMode: payload.score_mode,
            available: payload.available,
            missing: payload.missing,
            scanned: payload.scanned
          },
          ...items
        ].slice(0, 5)
      );
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : String(scanError));
    } finally {
      setBusy(false);
    }
  };

  const topRow = result?.rows.find((row) => row.status === "scanned");
  const prepareCandidateData = (row: ResearchSignalBatchRow) => {
    actions.setSettings({
      ...state.settings,
      symbol: row.code,
      exchange: row.exchange,
      csv_path: row.csv_path
    });
  };

  return (
    <div className="page-grid signal-radar-page">
      <section className="panel side-panel radar-controls">
        <div className="panel-title between">
          <span>信号雷达</span>
          <Radar size={17} />
        </div>
        <label className="search-box">
          <Search size={13} />
          <input aria-label="雷达搜索股票名称或代码" value={query} placeholder="按代码或名称筛选" onChange={(event) => setQuery(event.currentTarget.value)} />
        </label>
        <label className="field">
          扫描范围
          <select aria-label="扫描范围" value={universe} onChange={(event) => setUniverse(event.currentTarget.value as ScanUniverse)}>
            <option value="catalog">全部目录候选</option>
            <option value="local_csv">仅本地CSV</option>
            <option value="current">当前标的</option>
          </select>
        </label>
        <label className="field">
          评分模式
          <select aria-label="评分模式" value={scoreMode} onChange={(event) => setScoreMode(event.currentTarget.value as ResearchSignalBatchScoreMode)}>
            <option value="research">Chan/RSI研究分</option>
            <option value="volume_momentum">量价动量</option>
            <option value="chan_structure">缠论结构</option>
          </select>
        </label>
        <label className="field">
          扫描数量
          <input aria-label="扫描数量" type="number" min={1} max={50} value={limit} onChange={(event) => setLimit(clampNumber(event.currentTarget.value, 1, 50, DEFAULT_LIMIT))} />
        </label>
        <label className="field">
          最少K线
          <input
            aria-label="最少K线"
            type="number"
            min={20}
            max={500}
            value={minBars}
            onChange={(event) => setMinBars(clampNumber(event.currentTarget.value, 20, 500, DEFAULT_MIN_BARS))}
          />
        </label>
        <label className="field">
          回看窗口
          <input
            aria-label="回看窗口"
            type="number"
            min={20}
            max={500}
            value={lookback}
            onChange={(event) => setLookback(clampNumber(event.currentTarget.value, 20, 500, DEFAULT_LOOKBACK))}
          />
        </label>
        <ToolbarButton disabled={busy} icon={<Activity size={16} />} variant="primary" onClick={runScan}>
          {busy ? "扫描中..." : "批量扫描"}
        </ToolbarButton>
        <p className="caption">扫描只读取托管本地行情 CSV，不会自动联网下载或发出交易指令。</p>
        {error ? <p className="inline-alert">批量扫描失败：{error}</p> : null}
      </section>

      <main className="main-column">
        <section className="panel">
          <div className="panel-title between">
            <span>批量扫描概览</span>
            {result ? (
              <small>
                {universeLabel(result.universe)} · 可扫描 {result.available} / 缺数据 {result.missing}
              </small>
            ) : (
              <small>等待扫描</small>
            )}
          </div>
          <MetricStrip
            metrics={[
              { label: "候选数", value: result?.scanned ?? 0 },
              { label: "可扫描", value: result?.available ?? 0 },
              { label: "缺数据", value: result?.missing ?? 0 },
              { label: "当前最强", value: topRow ? `${topRow.code} ${directionLabel(topRow.score?.direction)}` : "-" }
            ]}
          />
        </section>

        <section className="panel radar-results">
          <div className="panel-title between">
            <span>{scoreModeTitle(result?.score_mode ?? scoreMode)}排行</span>
            {result ? (
              <a className="toolbar-button ghost compact" href={csvHref} download="signal-radar-scan.csv" aria-label="导出CSV">
                <Download size={14} />
                <span>导出CSV</span>
              </a>
            ) : null}
          </div>
          <DataTable rows={rankedRows} emptyText="暂无批量扫描结果" />
        </section>

        {history.length ? (
          <section className="panel radar-history">
            <div className="panel-title">历史扫描</div>
            <div className="history-list">
              {history.map((item) => (
                <div className="history-row" key={item.id}>
                  <strong>{item.query}</strong>
                  <span>
                    {scoreModeTitle(item.scoreMode)} · {universeLabel(item.universe)} · 可扫描 {item.available} / 缺数据 {item.missing}
                  </span>
                  <small>候选 {item.scanned}</small>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <section className="panel radar-card-grid">
          <div className="panel-title">雷达明细</div>
          {result?.rows.length ? (
            <div className="radar-result-cards">
              {result.rows.map((row) => (
	                <RadarResultCard key={`${row.code}-${row.status}`} row={row} onPrepareData={prepareCandidateData} />
              ))}
            </div>
          ) : (
            <div className="empty-table">点击批量扫描后展示本地托管行情候选的研究信号。</div>
          )}
        </section>
      </main>
    </div>
  );
}

function RadarResultCard({ row, onPrepareData }: { row: ResearchSignalBatchRow; onPrepareData: (row: ResearchSignalBatchRow) => void }) {
  const missing = row.status !== "scanned";
  return (
    <article className={missing ? "radar-result-card blocked" : "radar-result-card"}>
      <header>
        <strong>
          #{row.rank} {row.code} {row.name}
        </strong>
        <span>{missing ? "缺少CSV" : directionLabel(row.score?.direction)}</span>
      </header>
      <div className="radar-score-line">
        <span>综合 {formatNumber(row.score?.total_score)}</span>
        <span>置信 {row.score ? `${Math.round(row.score.confidence * 100)}%` : "-"}</span>
        <span>{row.exchange}</span>
      </div>
      {row.momentum ? (
        <div className="radar-score-line">
          <span>动量 {formatPercent(row.momentum.momentum_pct)}</span>
          <span>放量 {formatRatio(row.momentum.volume_ratio)}</span>
          <span>{row.momentum.trend_pass ? "趋势通过" : "趋势未过"}</span>
        </div>
      ) : null}
      {row.score?.chan_structure ? (
        <div className="radar-score-line">
          <span>分型 {row.score.chan_structure.fractal_count}</span>
          <span>笔 {row.score.chan_structure.stroke_count}</span>
          <span>中枢 {row.score.chan_structure.pivot_count}</span>
        </div>
      ) : null}
      <p>{row.latest_signal?.title ?? row.blockers[0]?.message ?? row.score?.summary ?? "暂无触发信号"}</p>
      {row.blockers.length ? (
        <div className="radar-blockers">
          <AlertTriangle size={14} />
          {row.blockers.map((blocker) => blocker.message).join("；")}
        </div>
      ) : null}
      {missing ? (
        <button className="toolbar-button ghost compact" type="button" aria-label={`准备 ${row.code} 数据`} onClick={() => onPrepareData(row)}>
          <Database size={14} />
          <span>准备数据</span>
        </button>
      ) : null}
    </article>
  );
}

function radarTableRows(rows: ResearchSignalBatchRow[]): Record<string, unknown>[] {
  const showMomentum = rows.some((row) => row.momentum);
  const showChanStructure = rows.some((row) => row.score?.chan_structure);
  return rows.map((row) => {
    const base = {
      排名: row.rank,
      代码: row.code,
      名称: row.name,
      状态: row.status === "scanned" ? "已扫描" : "缺少CSV",
      方向: directionLabel(row.score?.direction),
      综合分: row.score?.total_score ?? null,
      置信度: row.score ? `${Math.round(row.score.confidence * 100)}%` : null,
      最新信号: row.latest_signal?.title ?? row.blockers[0]?.code ?? "-"
    };
    return {
      ...base,
      ...(showMomentum
        ? {
            动量: formatPercent(row.momentum?.momentum_pct),
            放量: formatRatio(row.momentum?.volume_ratio),
            趋势: row.momentum ? (row.momentum.trend_pass ? "通过" : "未过") : "-"
          }
        : {}),
      ...(showChanStructure
        ? {
            分型: row.score?.chan_structure?.fractal_count ?? "-",
            笔: row.score?.chan_structure?.stroke_count ?? "-",
            中枢: row.score?.chan_structure?.pivot_count ?? "-",
            结构信号: row.score?.chan_structure?.latest_signal_title ?? "-"
          }
        : {})
    };
  });
}

function radarCsv(result: ResearchSignalBatchResponse): string {
  const showChanStructure = result.rows.some((row) => row.score?.chan_structure);
  const headers = [
    "rank",
    "code",
    "name",
    "exchange",
    "status",
    "total_score",
    "direction",
    "confidence",
    "latest_signal",
    "momentum_pct",
    "volume_ratio",
    "trend_pass",
    "latest_reason",
    "csv_path"
  ];
  if (showChanStructure) {
    headers.splice(headers.length - 1, 0, "fractal_count", "stroke_count", "pivot_count", "structure_signal");
  }
  const rows = result.rows.map((row) =>
    [
      row.rank,
      row.code,
      row.name,
      row.exchange,
      row.status,
      row.score?.total_score ?? "",
      row.score?.direction ?? "",
      row.score?.confidence ?? "",
      row.latest_signal?.title ?? "",
      row.momentum?.momentum_pct ?? "",
      row.momentum?.volume_ratio ?? "",
      row.momentum ? row.momentum.trend_pass : "",
      row.momentum?.latest_reason ?? "",
      ...(showChanStructure
        ? [
            row.score?.chan_structure?.fractal_count ?? "",
            row.score?.chan_structure?.stroke_count ?? "",
            row.score?.chan_structure?.pivot_count ?? "",
            row.score?.chan_structure?.latest_signal_title ?? ""
          ]
        : []),
      row.csv_path
    ]
      .map(csvCell)
      .join(",")
  );
  return [headers.join(","), ...rows].join("\n");
}

function csvCell(value: unknown): string {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function directionLabel(direction: string | null | undefined): string {
  if (direction === "bullish") return "看多";
  if (direction === "bearish") return "看空";
  if (direction === "neutral") return "中性";
  return "-";
}

function universeLabel(universe: string): string {
  if (universe === "local_csv") return "仅本地CSV";
  if (universe === "current") return "当前标的";
  return "全部目录";
}

function scoreModeTitle(mode: string | null | undefined): string {
  if (mode === "chan_structure") return "缠论结构";
  if (mode === "volume_momentum") return "量价动量";
  return "研究评分";
}

function formatNumber(value: number | null | undefined): string {
  return typeof value === "number" ? value.toFixed(2) : "-";
}

function formatPercent(value: number | null | undefined): string {
  return typeof value === "number" ? `${value.toFixed(2)}%` : "-";
}

function formatRatio(value: number | null | undefined): string {
  return typeof value === "number" ? `${value.toFixed(2)}倍` : "-";
}

function clampNumber(raw: string, min: number, max: number, fallback: number): number {
  const value = Number(raw);
  if (!Number.isFinite(value)) return fallback;
  return Math.max(min, Math.min(max, value));
}
