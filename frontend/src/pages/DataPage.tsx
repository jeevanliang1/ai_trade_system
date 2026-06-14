import { Download, FileDown, RefreshCw } from "lucide-react";

import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { ToolbarButton } from "../components/ToolbarButton";
import { priceOption } from "./chartOptions";
import type { PageProps } from "./pageTypes";

export function DataPage({ state, actions }: PageProps) {
  const update = (key: keyof typeof state.settings, value: string | number) => {
    actions.setSettings({ ...state.settings, [key]: value });
  };
  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">数据中心工作区</div>
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
        <div className="button-row">
          <ToolbarButton icon={<RefreshCw size={16} />} onClick={actions.loadData}>
            加载CSV
          </ToolbarButton>
          <ToolbarButton icon={<FileDown size={16} />} variant="primary" onClick={actions.demoData}>
            生成演示数据
          </ToolbarButton>
          <ToolbarButton icon={<Download size={16} />} onClick={actions.downloadData}>
            下载日线数据
          </ToolbarButton>
        </div>
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
        <ChartPanel title="价格走势" option={priceOption(state.bars)} height={360} />
        <section className="panel">
          <div className="panel-title">行情预览</div>
          <DataTable rows={state.bars.slice(-80).reverse() as unknown as Record<string, unknown>[]} />
        </section>
      </section>
    </div>
  );
}
