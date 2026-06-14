from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import date, timedelta
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ai_trade_system.analytics import calculate_backtest_metrics, drawdown_series
from ai_trade_system.backtest import BacktestConfig, BacktestResult, run_backtest
from ai_trade_system.data import fetch_akshare_daily_bars, read_bars_csv, write_bars_csv
from ai_trade_system.indicators import latest_indicator_snapshot
from ai_trade_system.llm import LLMResearchRequest, MockLLMProvider, build_research_prompt
from ai_trade_system.market import Bar
from ai_trade_system.paper_service import PaperTradingService
from ai_trade_system.portfolio import PortfolioStrategy, StrategyAllocation
from ai_trade_system.risk import RiskGuardrailConfig, evaluate_risk_guardrails
from ai_trade_system.stock_catalog import StockInfo, load_stock_catalog
from ai_trade_system.strategy import Strategy
from ai_trade_system.strategy_registry import (
    StrategySpec,
    create_strategy_template,
    discover_strategies,
    inspect_strategy_parameters,
    instantiate_strategy,
    read_strategy_source,
    save_strategy_source,
)
from ai_trade_system.web.components import apply_platform_theme, insight_box, section_header, topbar
from ai_trade_system.web.view_models import (
    bars_to_frame,
    drawdowns_to_frame,
    equity_curve_to_frame,
    indicator_snapshot_to_frame,
    llm_insight_to_sections,
    load_paper_events,
    metrics_to_frame,
    paper_events_to_frames,
    strategy_signals_to_frame,
    trades_to_frame,
)


def main() -> None:
    st.set_page_config(page_title="AI量化平台", page_icon="📈", layout="wide")
    apply_platform_theme()
    settings = _render_sidebar()
    bars = _load_bars(settings["csv_path"])
    topbar(
        "AI量化平台",
        [
            _selected_stock_label(settings),
            f"数据日期 {settings['start_date']} - {settings['end_date']}",
            "MockProvider 已连接",
            "仅研究与纸面交易",
        ],
    )

    tabs = st.tabs(["总览", "数据中心", "策略工坊", "组合实验室", "回测中心", "AI研究员", "纸面交易", "风控"])
    with tabs[0]:
        _render_overview(settings, bars)
    with tabs[1]:
        _render_data_center(settings, bars)
    with tabs[2]:
        _render_strategy_workbench(settings, bars)
    with tabs[3]:
        _render_portfolio_lab(settings, bars)
    with tabs[4]:
        _render_backtest_center(settings, bars)
    with tabs[5]:
        _render_ai_researcher(settings, bars)
    with tabs[6]:
        _render_paper_trading(settings, bars)
    with tabs[7]:
        _render_risk_center(settings)
    apply_platform_theme()


def _render_sidebar() -> dict[str, Any]:
    st.sidebar.title("AI量化平台")
    st.sidebar.caption("A股研究 · 回测 · 纸面交易")
    st.sidebar.divider()
    st.sidebar.subheader("市场数据")
    catalog = load_stock_catalog()
    if catalog:
        selected_stock = st.sidebar.selectbox(
            "股票搜索",
            catalog,
            index=_default_stock_index(catalog, "000001"),
            format_func=_stock_option_label,
        )
        manual_symbol = st.sidebar.checkbox("手动输入股票", value=False)
        if manual_symbol:
            symbol = st.sidebar.text_input("股票代码", value=selected_stock.code).strip()
            exchange = st.sidebar.selectbox("交易所", ["SZSE", "SSE", "BSE"], index=_exchange_index(selected_stock.exchange))
            stock_name = ""
        else:
            symbol = selected_stock.code
            exchange = selected_stock.exchange
            stock_name = selected_stock.name
            st.sidebar.caption(f"已选择：{selected_stock.name}")
    else:
        st.sidebar.info("未加载本地股票目录，可先手动输入代码，或运行 `ai-trade stocks refresh`。")
        symbol = st.sidebar.text_input("股票代码", value="000001").strip()
        exchange = st.sidebar.selectbox("交易所", ["SZSE", "SSE", "BSE"], index=0)
        stock_name = ""
    start_date = st.sidebar.text_input("开始日期", value="20220101")
    end_date = st.sidebar.text_input("结束日期", value="20250516")
    adjust = st.sidebar.selectbox("复权", ["qfq", "hfq", ""], index=0, format_func=lambda value: value or "不复权")
    csv_path_key = _sync_csv_path_for_symbol(st.session_state, symbol)
    csv_path = st.sidebar.text_input("CSV路径", key=csv_path_key)
    log_path = st.sidebar.text_input("纸面交易日志", value="logs/paper_events.jsonl")

    st.sidebar.subheader("账户与执行")
    initial_cash = st.sidebar.number_input("初始资金", min_value=1_000.0, value=100_000.0, step=10_000.0)
    commission_rate = st.sidebar.number_input("手续费率", min_value=0.0, max_value=0.1, value=0.0003, step=0.0001, format="%.4f")
    slippage = st.sidebar.number_input("滑点", min_value=0.0, max_value=10.0, value=0.01, step=0.01)
    max_order_cash = st.sidebar.number_input("单笔最大金额", min_value=1_000.0, value=50_000.0, step=5_000.0)

    st.sidebar.subheader("风控")
    max_drawdown_pct = st.sidebar.number_input("最大回撤保护(%)", min_value=1.0, max_value=80.0, value=20.0, step=1.0)
    min_cash_balance = st.sidebar.number_input("最小现金余额", min_value=0.0, value=0.0, step=1_000.0)
    max_position_shares = st.sidebar.number_input("最大持仓股数", min_value=100, value=50_000, step=100)

    return {
        "symbol": symbol,
        "stock_name": stock_name,
        "exchange": exchange,
        "start_date": start_date,
        "end_date": end_date,
        "adjust": adjust,
        "csv_path": csv_path,
        "log_path": log_path,
        "initial_cash": float(initial_cash),
        "commission_rate": float(commission_rate),
        "slippage": float(slippage),
        "max_order_cash": float(max_order_cash),
        "max_drawdown_pct": float(max_drawdown_pct),
        "min_cash_balance": float(min_cash_balance),
        "max_position_shares": int(max_position_shares),
    }


def _stock_option_label(stock: StockInfo) -> str:
    return f"{stock.code} {stock.name} {stock.exchange}"


def _default_stock_index(catalog: list[StockInfo], code: str) -> int:
    for index, stock in enumerate(catalog):
        if stock.code == code:
            return index
    return 0


def _exchange_index(exchange: str) -> int:
    exchanges = ["SZSE", "SSE", "BSE"]
    return exchanges.index(exchange) if exchange in exchanges else 0


def _selected_stock_label(settings: dict[str, Any]) -> str:
    name = settings.get("stock_name")
    return f"{settings['symbol']} {name} {settings['exchange']}" if name else f"{settings['symbol']} {settings['exchange']}"


def _sync_csv_path_for_symbol(session_state, symbol: str) -> str:
    csv_path_key = "market_csv_path"
    symbol_key = "market_csv_symbol"
    if session_state.get(symbol_key) != symbol:
        session_state[csv_path_key] = f"data/{symbol}_daily.csv"
        session_state[symbol_key] = symbol
    return csv_path_key


def _render_overview(settings: dict[str, Any], bars: list) -> None:
    section_header("平台总览", "一眼确认数据、策略、AI研究和风险状态。")
    data_frame = bars_to_frame(bars)
    events = load_paper_events(settings["log_path"])
    recent_result = st.session_state.get("last_backtest")
    recent_insight = st.session_state.get("last_ai_insight")
    metrics_cols = st.columns(5)
    metrics_cols[0].metric("K线数量", str(len(bars)))
    metrics_cols[1].metric("最新交易日", "-" if data_frame.empty else str(data_frame.iloc[-1]["trading_day"]))
    metrics_cols[2].metric("策略数量", str(len(discover_strategies())))
    metrics_cols[3].metric("纸面事件", str(len(events)))
    metrics_cols[4].metric("AI观点", recent_insight.direction if recent_insight else "未生成")

    left, center, right = st.columns([1.1, 1.7, 1.1])
    with left:
        section_header("数据健康", f"当前CSV：{settings['csv_path']}")
        if data_frame.empty:
            st.info("暂无本地数据。请到数据中心下载或放入CSV。")
        else:
            st.dataframe(_data_health_frame(data_frame), width="stretch", hide_index=True)
    with center:
        section_header("最近回测")
        if recent_result:
            _render_backtest_result(settings, bars, recent_result, compact=True)
        elif data_frame.empty:
            st.info("加载数据并运行回测后，这里会显示资金曲线和交易摘要。")
        else:
            st.plotly_chart(_price_line_figure(data_frame), width="stretch", key="overview_price_line")
    with right:
        section_header("AI研究员", "技术指标 + 信息面 + 风控约束")
        if recent_insight:
            _render_ai_insight(recent_insight)
        else:
            insight_box("等待研究请求", "进入 AI研究员 页，输入信息面摘要并生成结构化观点。")


def _render_data_center(settings: dict[str, Any], bars: list) -> None:
    section_header("数据中心", "下载、加载和检查A股日线数据。")
    control_cols = st.columns([1, 1, 1.4])
    with control_cols[0]:
        if st.button("下载日线数据", type="primary"):
            try:
                downloaded = fetch_akshare_daily_bars(
                    symbol=settings["symbol"],
                    start_date=settings["start_date"],
                    end_date=settings["end_date"],
                    exchange=settings["exchange"],
                    adjust=settings["adjust"],
                )
                write_bars_csv(downloaded, settings["csv_path"])
                st.success(f"已写入 {len(downloaded)} 根K线：{settings['csv_path']}")
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"下载失败：{exc}")
        if st.button("生成演示数据"):
            demo = _demo_bars(settings["symbol"], settings["exchange"])
            write_bars_csv(demo, settings["csv_path"])
            st.success(f"已生成 {len(demo)} 根演示K线：{settings['csv_path']}")
            st.rerun()
    with control_cols[1]:
        st.caption("本地CSV")
        st.code(settings["csv_path"], language="text")
    with control_cols[2]:
        st.caption("数据源顺序")
        st.write("Eastmoney -> Tencent -> Sina；网络不可用时可直接放入本地 CSV。")

    if not bars:
        st.info("暂无可展示数据。")
        return

    frame = bars_to_frame(bars)
    _render_data_summary(frame)
    st.plotly_chart(_price_line_figure(frame), width="stretch", key="data_center_price_line")
    st.dataframe(frame.tail(300), width="stretch", hide_index=True)


def _render_strategy_workbench(settings: dict[str, Any], bars: list) -> None:
    section_header("策略工坊", "管理策略源码、参数和信号预览。")
    st.warning("用户策略会作为本机 Python 代码执行。只编辑和运行你信任的策略文件。")
    specs = discover_strategies()
    if not specs:
        st.error("没有发现可用策略。")
        return

    left, right = st.columns([1.05, 1.8])
    with left:
        selected_spec = _select_strategy_spec(specs, "strategy_manager")
        meta_cols = st.columns(2)
        meta_cols[0].metric("来源", "内置" if selected_spec.source == "builtin" else "用户")
        meta_cols[1].metric("可编辑", "否" if selected_spec.source == "builtin" else "是")
        st.caption(f"策略ID：{selected_spec.id}")
        if selected_spec.source == "user" and selected_spec.path:
            source = read_strategy_source(selected_spec.path)
            edited = st.text_area("策略源码", value=source, height=360, key=f"strategy_source_{selected_spec.id}")
            if st.button("保存策略", type="primary"):
                try:
                    save_strategy_source("strategies", selected_spec.path.name, edited)
                    st.success("策略已保存。")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.info("内置策略不可直接编辑。可在下方创建用户策略模板。")

        with st.expander("新建策略模板", expanded=False):
            new_file = st.text_input("文件名", value="my_strategy.py")
            new_class = st.text_input("策略类名", value="MyStrategy")
            template = create_strategy_template(new_class)
            st.code(template, language="python")
            if st.button("创建策略文件"):
                try:
                    path = save_strategy_source("strategies", new_file, template)
                    st.success(f"已创建：{path}")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    with right:
        strategy = _render_strategy_picker(settings, "preview")
        if not bars:
            st.info("请先下载或准备CSV数据，策略页会基于行情预览信号。")
            return
        if strategy is None:
            return
        signals = strategy_signals_to_frame(bars, strategy)
        bars_frame = bars_to_frame(bars)
        metric_cols = st.columns(3)
        metric_cols[0].metric("信号数量", str(len(signals)))
        metric_cols[1].metric("买入信号", str(len(signals[signals["action"] == "buy"])) if not signals.empty else "0")
        metric_cols[2].metric("卖出信号", str(len(signals[signals["action"] == "sell"])) if not signals.empty else "0")
        st.plotly_chart(_signal_figure(bars_frame, signals), width="stretch", key="strategy_signal_preview")
        st.dataframe(signals, width="stretch", hide_index=True)


def _render_portfolio_lab(settings: dict[str, Any], bars: list) -> None:
    section_header("组合实验室", "将多个策略按权重、票数或优先级合成为一个组合策略。")
    portfolio = _render_portfolio_builder(settings, "portfolio_lab")
    if not portfolio:
        return
    if not bars:
        st.info("请先准备CSV数据，组合实验室会基于行情预览组合信号。")
        return
    signals = strategy_signals_to_frame(bars, portfolio)
    left, right = st.columns([1.2, 1.7])
    with left:
        st.dataframe(_portfolio_allocation_frame(portfolio), width="stretch", hide_index=True)
        if portfolio.last_breakdown.active_signals:
            st.json(
                {
                    "buy_score": portfolio.last_breakdown.buy_score,
                    "sell_score": portfolio.last_breakdown.sell_score,
                    "active_signals": portfolio.last_breakdown.active_signals,
                    "mode": portfolio.last_breakdown.mode,
                }
            )
    with right:
        st.plotly_chart(_signal_figure(bars_to_frame(bars), signals), width="stretch", key="portfolio_signal_preview")
        st.dataframe(signals, width="stretch", hide_index=True)


def _render_backtest_center(settings: dict[str, Any], bars: list) -> None:
    section_header("回测中心", "运行单策略或组合策略回测，查看收益、回撤、买卖点和交易明细。")
    if not bars:
        st.info("请先下载或准备CSV数据。")
        return

    mode = st.radio("回测对象", ["单策略", "组合策略"], horizontal=True)
    strategy: Strategy | None
    if mode == "单策略":
        strategy = _render_strategy_picker(settings, "backtest_single")
    else:
        strategy = _render_portfolio_builder(settings, "backtest_portfolio")
    if strategy is None:
        return

    if st.button("运行回测", type="primary"):
        result = _safe_run_backtest(settings, bars, strategy)
        if result:
            st.session_state["last_backtest"] = result

    result = st.session_state.get("last_backtest")
    if result:
        _render_backtest_result(settings, bars, result)


def _render_ai_researcher(settings: dict[str, Any], bars: list) -> None:
    section_header("AI研究员", "MockProvider 按技术指标、信息面和风控上下文生成结构化研究观点。")
    if not bars:
        st.info("请先准备CSV数据，AI研究员需要技术指标快照。")
        return

    snapshot = latest_indicator_snapshot(bars)
    left, right = st.columns([1.15, 1.6])
    with left:
        st.dataframe(indicator_snapshot_to_frame(snapshot), width="stretch", hide_index=True)
        prompt_mode = st.selectbox("提示词模式", ["balanced", "conservative", "aggressive"], index=0)
        horizon = st.selectbox("研究周期", ["3个交易日", "5个交易日", "20个交易日"], index=1)
        information_text = st.text_area(
            "信息面摘要",
            value="政策支持流动性改善；行业景气度回升；关注短线追高风险。",
            height=150,
        )
        show_prompt = st.checkbox("显示Prompt快照", value=False)
        request = LLMResearchRequest(
            symbol=settings["symbol"],
            horizon=horizon,
            indicator_snapshot=snapshot,
            information_notes=[line.strip() for line in information_text.replace("；", "\n").splitlines() if line.strip()],
            risk_context={"max_drawdown_pct": settings["max_drawdown_pct"], "max_order_cash": settings["max_order_cash"]},
            prompt_mode=prompt_mode,
        )
        if show_prompt:
            st.code(build_research_prompt(request), language="text")
        if st.button("生成AI观点", type="primary"):
            st.session_state["last_ai_insight"] = MockLLMProvider().generate_insight(request)

    with right:
        insight = st.session_state.get("last_ai_insight") or MockLLMProvider().generate_insight(request)
        _render_ai_insight(insight)


def _render_paper_trading(settings: dict[str, Any], bars: list) -> None:
    section_header("纸面交易", "重放CSV行情，经过策略和风控后输出JSONL事件日志。")
    strategy = _render_strategy_picker(settings, "paper") if bars else None
    left, right = st.columns([1, 1])
    with left:
        if st.button("运行纸面交易", type="primary", disabled=not bool(bars)):
            if strategy is None:
                return
            service = PaperTradingService(
                strategy=strategy,
                initial_cash=settings["initial_cash"],
                commission_rate=settings["commission_rate"],
                slippage=settings["slippage"],
                max_order_cash=settings["max_order_cash"],
            )
            events = service.run(bars, log_path=settings["log_path"])
            st.success(f"已写入 {len(events)} 条事件：{settings['log_path']}")
    with right:
        st.caption("当前日志")
        st.code(settings["log_path"], language="text")

    events = load_paper_events(settings["log_path"])
    if not events:
        st.info("暂无纸面交易日志。")
        return
    orders, equity, summary = paper_events_to_frames(events)
    metric_cols = st.columns(3)
    metric_cols[0].metric("事件数", str(len(events)))
    metric_cols[1].metric("订单事件", str(len(orders)))
    metric_cols[2].metric("最终权益", f"{summary.get('final_equity', 0):,.2f}" if summary else "-")
    if not equity.empty:
        st.plotly_chart(_paper_equity_figure(equity), width="stretch", key="paper_equity_curve")
    st.dataframe(orders, width="stretch", hide_index=True)
    st.dataframe(equity, width="stretch", hide_index=True)


def _render_risk_center(settings: dict[str, Any]) -> None:
    section_header("风控", "集中查看确定性风控阈值。AI观点只提供研究信号，不能绕过这些约束。")
    result = st.session_state.get("last_backtest")
    metrics_dict = {"max_drawdown_pct": 0.0}
    if result:
        metrics = calculate_backtest_metrics(result.equity_curve, result.trades, settings["initial_cash"])
        metrics_dict["max_drawdown_pct"] = metrics.max_drawdown_pct
        st.dataframe(metrics_to_frame(metrics), width="stretch", hide_index=True)
    config = _risk_config(settings)
    status = evaluate_risk_guardrails(metrics_dict, config)
    if status.ok:
        st.success("当前配置未触发主要风控警示。")
    else:
        for warning in status.warnings:
            st.warning(warning)
    st.dataframe(
        pd.DataFrame(
            [
                {"guardrail": "最大回撤保护(%)", "value": config.max_drawdown_pct},
                {"guardrail": "单笔最大金额", "value": config.max_order_cash},
                {"guardrail": "最小现金余额", "value": config.min_cash_balance},
                {"guardrail": "最大持仓股数", "value": config.max_position_shares},
            ]
        ),
        width="stretch",
        hide_index=True,
    )


def _safe_run_backtest(settings: dict[str, Any], bars: list, strategy: Strategy) -> BacktestResult | None:
    try:
        return run_backtest(
            bars,
            strategy,
            BacktestConfig(
                initial_cash=settings["initial_cash"],
                commission_rate=settings["commission_rate"],
                slippage=settings["slippage"],
                max_order_cash=settings["max_order_cash"],
            ),
        )
    except ValueError as exc:
        st.error(f"回测参数错误：{exc}")
        return None


def _render_backtest_result(settings: dict[str, Any], bars: list, result: BacktestResult, compact: bool = False) -> None:
    equity_frame = equity_curve_to_frame(result.equity_curve)
    trade_frame = trades_to_frame(result.trades)
    bars_frame = bars_to_frame(bars)
    metrics = calculate_backtest_metrics(result.equity_curve, result.trades, settings["initial_cash"])
    drawdown_frame = drawdowns_to_frame(drawdown_series(result.equity_curve))
    risk_status = evaluate_risk_guardrails({"max_drawdown_pct": metrics.max_drawdown_pct}, _risk_config(settings))

    metric_cols = st.columns(5)
    metric_cols[0].metric("最终权益", f"{metrics.final_equity:,.2f}")
    metric_cols[1].metric("累计收益", f"{metrics.total_return_pct:.2f}%")
    metric_cols[2].metric("最大回撤", f"{metrics.max_drawdown_pct:.2f}%")
    metric_cols[3].metric("交易次数", str(metrics.trade_count))
    metric_cols[4].metric("风控状态", "通过" if risk_status.ok else "警示")
    chart_prefix = "overview_backtest" if compact else "backtest_center"
    st.plotly_chart(_price_figure(bars_frame, trade_frame), width="stretch", key=f"{chart_prefix}_price")
    if not compact:
        left, right = st.columns([1.2, 1])
        with left:
            st.plotly_chart(_equity_figure(equity_frame), width="stretch", key=f"{chart_prefix}_equity")
        with right:
            st.plotly_chart(_drawdown_figure(drawdown_frame), width="stretch", key=f"{chart_prefix}_drawdown")
        st.dataframe(metrics_to_frame(metrics), width="stretch", hide_index=True)
        st.dataframe(trade_frame, width="stretch", hide_index=True)


def _render_ai_insight(insight) -> None:
    sections = llm_insight_to_sections(insight)
    summary = sections["summary"]
    tone = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}.get(summary["direction"], summary["direction"])
    st.metric("AI观点", tone, f"置信度 {summary['confidence']}%")
    st.caption(f"{summary['provider']} · {summary['prompt_version']} · {summary['created_at']}")
    st.subheader("建议动作")
    st.write(summary["suggested_action"])
    st.subheader("技术证据")
    st.write("\n".join(f"- {item}" for item in sections["technical_evidence"]))
    st.subheader("信息面证据")
    st.write("\n".join(f"- {item}" for item in sections["information_evidence"]))
    st.subheader("风险提示")
    for warning in sections["risk_warnings"]:
        st.warning(warning)


def _render_data_summary(frame: pd.DataFrame) -> None:
    cols = st.columns(5)
    cols[0].metric("K线数量", str(len(frame)))
    cols[1].metric("起始日期", str(frame.iloc[0]["trading_day"]))
    cols[2].metric("结束日期", str(frame.iloc[-1]["trading_day"]))
    cols[3].metric("最新收盘", f"{frame.iloc[-1]['close_price']:.2f}")
    cols[4].metric("成交额", f"{frame.iloc[-1]['turnover']:,.0f}")


def _load_bars(path: str):
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    try:
        return read_bars_csv(csv_path)
    except Exception as exc:
        st.error(f"读取CSV失败：{exc}")
        return []


def _demo_bars(symbol: str, exchange: str, count: int = 260) -> list[Bar]:
    start = date(2024, 1, 2)
    bars: list[Bar] = []
    close = 10.0
    for index in range(count):
        drift = 0.015 if index < count * 0.6 else -0.005
        wave = math.sin(index / 8) * 0.08
        close = max(2.0, close + drift + wave)
        open_price = close - 0.08 + math.sin(index / 5) * 0.04
        high_price = max(open_price, close) + 0.18
        low_price = min(open_price, close) - 0.18
        volume = 1_000_000 + index * 2500 + abs(math.sin(index / 6)) * 120_000
        bars.append(
            Bar(
                symbol=symbol,
                exchange=exchange,
                trading_day=start + timedelta(days=index),
                open_price=round(open_price, 2),
                high_price=round(high_price, 2),
                low_price=round(low_price, 2),
                close_price=round(close, 2),
                volume=round(volume, 2),
                turnover=round(volume * close, 2),
            )
        )
    return bars


def _select_strategy_spec(specs: list[StrategySpec], key_prefix: str) -> StrategySpec:
    labels = [_strategy_label(spec) for spec in specs]
    selected_label = st.selectbox("选择策略", labels, key=f"{key_prefix}_strategy_select")
    return specs[labels.index(selected_label)]


def _render_strategy_picker(settings: dict[str, Any], key_prefix: str) -> Strategy | None:
    specs = discover_strategies()
    if not specs:
        st.error("没有发现可用策略。")
        return None
    spec = _select_strategy_spec(specs, key_prefix)
    params = {}
    with st.expander("策略参数", expanded=True):
        for param in inspect_strategy_parameters(spec):
            params[param.name] = _render_strategy_param_input(param, settings, key_prefix)
    try:
        return instantiate_strategy(spec, params)
    except Exception as exc:
        st.error(f"策略实例化失败：{exc}")
        return None


def _render_portfolio_builder(settings: dict[str, Any], key_prefix: str) -> PortfolioStrategy | None:
    specs = discover_strategies()
    if not specs:
        st.error("没有发现可用策略。")
        return None
    labels = [_strategy_label(spec) for spec in specs]
    default_labels = labels[: min(2, len(labels))]
    selected = st.multiselect("添加策略", labels, default=default_labels, key=f"{key_prefix}_selected")
    mode = st.selectbox("组合模式", ["weighted_vote", "equal_vote", "first_active"], key=f"{key_prefix}_mode")
    ai_adjust = st.toggle("AI参与评分", value=False, key=f"{key_prefix}_ai_adjust")
    allocations: list[StrategyAllocation] = []
    for index, label in enumerate(selected):
        spec = specs[labels.index(label)]
        with st.expander(f"{label} 参数", expanded=index == 0):
            enabled = st.checkbox("启用", value=True, key=f"{key_prefix}_{index}_enabled")
            weight = st.slider("组合权重", min_value=0.0, max_value=1.0, value=round(1 / max(1, len(selected)), 2), step=0.05, key=f"{key_prefix}_{index}_weight")
            if ai_adjust and st.session_state.get("last_ai_insight") and st.session_state["last_ai_insight"].direction == "bullish":
                weight = min(1.0, weight + 0.05)
            params = {
                param.name: _render_strategy_param_input(param, settings, f"{key_prefix}_{index}")
                for param in inspect_strategy_parameters(spec)
            }
            try:
                allocations.append(StrategyAllocation(spec.name, instantiate_strategy(spec, params), weight, enabled))
            except Exception as exc:
                st.error(f"{spec.name} 实例化失败：{exc}")
    if not allocations:
        st.info("请至少添加一个策略。")
        return None
    return PortfolioStrategy(allocations, mode=mode)


def _render_strategy_param_input(param, settings: dict[str, Any], key_prefix: str):
    key = f"{key_prefix}_strategy_param_{param.name}"
    if param.name == "symbol":
        return st.text_input(param.name, value=settings["symbol"], key=key)
    default = param.default
    if isinstance(default, bool):
        return st.checkbox(param.name, value=default, key=key)
    if isinstance(default, int):
        return int(st.number_input(param.name, value=default, step=1, key=key))
    if isinstance(default, float):
        return float(st.number_input(param.name, value=default, key=key))
    return st.text_input(param.name, value="" if default is None else str(default), key=key)


def _strategy_label(spec: StrategySpec) -> str:
    source = "内置" if spec.source == "builtin" else "用户"
    return f"{spec.name} ({source})"


def _risk_config(settings: dict[str, Any]) -> RiskGuardrailConfig:
    return RiskGuardrailConfig(
        max_drawdown_pct=settings["max_drawdown_pct"],
        max_order_cash=settings["max_order_cash"],
        min_cash_balance=settings["min_cash_balance"],
        max_position_shares=settings["max_position_shares"],
    )


def _data_health_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"项目": "股票代码", "状态": str(frame.iloc[-1]["symbol"])},
            {"项目": "交易所", "状态": str(frame.iloc[-1]["exchange"])},
            {"项目": "起始日期", "状态": str(frame.iloc[0]["trading_day"])},
            {"项目": "结束日期", "状态": str(frame.iloc[-1]["trading_day"])},
            {"项目": "行数", "状态": str(len(frame))},
        ]
    )


def _portfolio_allocation_frame(strategy: PortfolioStrategy) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "策略": allocation.name,
                "权重": allocation.weight,
                "启用": allocation.enabled,
            }
            for allocation in strategy.allocations
        ]
    )


def _price_figure(bars: pd.DataFrame, trades: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Candlestick(
            x=bars["trading_day"],
            open=bars["open_price"],
            high=bars["high_price"],
            low=bars["low_price"],
            close=bars["close_price"],
            name="价格",
        )
    )
    if not trades.empty:
        buys = trades[trades["side"] == "buy"]
        sells = trades[trades["side"] == "sell"]
        figure.add_trace(go.Scatter(x=buys["trading_day"], y=buys["price"], mode="markers", marker={"color": "#16a34a", "size": 10, "symbol": "triangle-up"}, name="买入"))
        figure.add_trace(go.Scatter(x=sells["trading_day"], y=sells["price"], mode="markers", marker={"color": "#dc2626", "size": 10, "symbol": "triangle-down"}, name="卖出"))
    figure.update_layout(template="plotly_white", height=430, margin={"l": 10, "r": 10, "t": 30, "b": 10}, xaxis_rangeslider_visible=False)
    return figure


def _price_line_figure(bars: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=bars["trading_day"], y=bars["close_price"], mode="lines", name="收盘价", line={"color": "#2563eb"}))
    figure.update_layout(template="plotly_white", height=330, margin={"l": 10, "r": 10, "t": 20, "b": 10})
    return figure


def _signal_figure(bars: pd.DataFrame, signals: pd.DataFrame) -> go.Figure:
    figure = _price_line_figure(bars)
    if not signals.empty:
        buys = signals[signals["action"] == "buy"]
        sells = signals[signals["action"] == "sell"]
        figure.add_trace(go.Scatter(x=buys["trading_day"], y=buys["price"], mode="markers", marker={"color": "#16a34a", "size": 10, "symbol": "triangle-up"}, name="买入信号"))
        figure.add_trace(go.Scatter(x=sells["trading_day"], y=sells["price"], mode="markers", marker={"color": "#dc2626", "size": 10, "symbol": "triangle-down"}, name="卖出信号"))
    figure.update_layout(height=390)
    return figure


def _equity_figure(equity: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=equity["trading_day"], y=equity["equity"], mode="lines", name="权益", line={"color": "#16a34a"}))
    figure.add_trace(go.Scatter(x=equity["trading_day"], y=equity["cash"], mode="lines", name="现金", line={"color": "#64748b"}))
    figure.update_layout(template="plotly_white", height=320, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    return figure


def _drawdown_figure(drawdown: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=drawdown["trading_day"], y=drawdown["drawdown_pct"], mode="lines", fill="tozeroy", name="回撤", line={"color": "#dc2626"}))
    figure.update_layout(template="plotly_white", height=320, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    return figure


def _paper_equity_figure(equity: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=equity["trading_day"], y=equity["equity"], mode="lines", name="纸面权益", line={"color": "#2563eb"}))
    figure.update_layout(template="plotly_white", height=330, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    return figure


if __name__ == "__main__":
    main()
