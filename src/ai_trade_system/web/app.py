from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import fetch_akshare_daily_bars, read_bars_csv, write_bars_csv
from ai_trade_system.paper_service import PaperTradingService
from ai_trade_system.strategy_registry import (
    create_strategy_template,
    discover_strategies,
    inspect_strategy_parameters,
    instantiate_strategy,
    read_strategy_source,
    save_strategy_source,
)
from ai_trade_system.web.view_models import (
    bars_to_frame,
    equity_curve_to_frame,
    load_paper_events,
    paper_events_to_frames,
    strategy_signals_to_frame,
    trades_to_frame,
)


def main() -> None:
    st.set_page_config(page_title="A股量化操作台", layout="wide")
    st.title("A股量化操作台")

    settings = _render_sidebar()
    tab_data, tab_strategy, tab_backtest, tab_paper = st.tabs(["数据", "策略", "回测", "纸面交易"])

    with tab_data:
        _render_data_tab(settings)
    with tab_strategy:
        _render_strategy_tab(settings)
    with tab_backtest:
        _render_backtest_tab(settings)
    with tab_paper:
        _render_paper_tab(settings)


def _render_sidebar() -> dict:
    st.sidebar.header("参数")
    symbol = st.sidebar.text_input("股票代码", value="000001").strip()
    exchange = st.sidebar.selectbox("交易所", ["SZSE", "SSE"], index=0)
    start_date = st.sidebar.text_input("开始日期", value="20240101")
    end_date = st.sidebar.text_input("结束日期", value="20241231")
    csv_path = st.sidebar.text_input("CSV路径", value=f"data/{symbol}_daily.csv")
    log_path = st.sidebar.text_input("纸面交易日志", value="logs/paper_events.jsonl")

    st.sidebar.header("账户")
    initial_cash = st.sidebar.number_input("初始资金", min_value=1_000.0, value=100_000.0, step=10_000.0)
    commission_rate = st.sidebar.number_input("手续费率", min_value=0.0, max_value=0.1, value=0.0003, step=0.0001, format="%.4f")
    slippage = st.sidebar.number_input("滑点", min_value=0.0, max_value=10.0, value=0.01, step=0.01)
    max_order_cash = st.sidebar.number_input("单笔最大金额", min_value=1_000.0, value=50_000.0, step=5_000.0)

    return {
        "symbol": symbol,
        "exchange": exchange,
        "start_date": start_date,
        "end_date": end_date,
        "csv_path": csv_path,
        "log_path": log_path,
        "initial_cash": float(initial_cash),
        "commission_rate": float(commission_rate),
        "slippage": float(slippage),
        "max_order_cash": float(max_order_cash),
    }


def _render_data_tab(settings: dict) -> None:
    left, right = st.columns([1, 1])
    with left:
        if st.button("下载日线数据", type="primary"):
            try:
                bars = fetch_akshare_daily_bars(
                    symbol=settings["symbol"],
                    start_date=settings["start_date"],
                    end_date=settings["end_date"],
                    exchange=settings["exchange"],
                )
                write_bars_csv(bars, settings["csv_path"])
                st.success(f"已写入 {len(bars)} 根K线：{settings['csv_path']}")
            except RuntimeError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"下载失败：{exc}")

    with right:
        st.caption(f"当前CSV：{settings['csv_path']}")

    bars = _load_bars(settings["csv_path"])
    if not bars:
        st.info("暂无可展示数据。")
        return

    frame = bars_to_frame(bars)
    _render_data_summary(frame)
    st.dataframe(frame.tail(200), width="stretch", hide_index=True)


def _render_backtest_tab(settings: dict) -> None:
    bars = _load_bars(settings["csv_path"])
    if not bars:
        st.info("请先下载或准备CSV数据。")
        return

    strategy = _render_strategy_picker(settings, key_prefix="backtest")
    if strategy is None:
        return

    try:
        result = run_backtest(
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
        return

    equity_frame = equity_curve_to_frame(result.equity_curve)
    trade_frame = trades_to_frame(result.trades)
    bars_frame = bars_to_frame(bars)
    total_return = (result.final_equity / settings["initial_cash"] - 1) if settings["initial_cash"] else 0

    metric_cols = st.columns(3)
    metric_cols[0].metric("最终权益", f"{result.final_equity:,.2f}")
    metric_cols[1].metric("交易次数", str(len(result.trades)))
    metric_cols[2].metric("收益率", f"{total_return:.2%}")

    st.plotly_chart(_price_figure(bars_frame, trade_frame), width="stretch")
    st.plotly_chart(_equity_figure(equity_frame), width="stretch")
    st.dataframe(trade_frame, width="stretch", hide_index=True)


def _render_strategy_tab(settings: dict) -> None:
    st.subheader("策略管理")
    st.warning("用户策略会作为本机 Python 代码执行。只编辑和运行你信任的策略文件。")

    specs = discover_strategies()
    if not specs:
        st.error("没有发现可用策略。")
        return
    labels = [_strategy_label(spec) for spec in specs]
    selected_label = st.selectbox("选择策略", labels, key="strategy_manager_select")
    selected_spec = specs[labels.index(selected_label)]

    meta_cols = st.columns(3)
    meta_cols[0].metric("策略名称", selected_spec.name)
    meta_cols[1].metric("来源", "内置" if selected_spec.source == "builtin" else "用户")
    meta_cols[2].metric("可编辑", "否" if selected_spec.source == "builtin" else "是")
    st.caption(f"策略ID：{selected_spec.id}")

    if selected_spec.source == "user" and selected_spec.path:
        source = read_strategy_source(selected_spec.path)
        edited = st.text_area("策略源码", value=source, height=420, key=f"strategy_source_{selected_spec.id}")
        if st.button("保存策略", type="primary"):
            try:
                save_strategy_source("strategies", selected_spec.path.name, edited)
                st.success("策略已保存。页面会在下次交互时重新加载策略。")
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.info("内置策略不可在页面中直接编辑。可以在下方新建一个用户策略模板后修改。")

    with st.expander("新建策略模板"):
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

    bars = _load_bars(settings["csv_path"])
    if not bars:
        st.info("请先下载或准备CSV数据，策略页会基于行情预览信号。")
        return

    st.divider()
    st.subheader("信号预览")
    strategy = _render_strategy_picker(settings, key_prefix="preview")
    if strategy is None:
        return

    signals = strategy_signals_to_frame(bars, strategy)
    bars_frame = bars_to_frame(bars)
    st.metric("信号数量", str(len(signals)))
    st.plotly_chart(_signal_figure(bars_frame, signals), width="stretch")
    st.dataframe(signals, width="stretch", hide_index=True)


def _render_paper_tab(settings: dict) -> None:
    bars = _load_bars(settings["csv_path"])
    strategy = _render_strategy_picker(settings, key_prefix="paper") if bars else None
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
        st.caption(f"当前日志：{settings['log_path']}")

    events = load_paper_events(settings["log_path"])
    if not events:
        st.info("暂无纸面交易日志。")
        return

    orders, equity, summary = paper_events_to_frames(events)
    if summary.get("final_equity") is not None:
        st.metric("最终权益", f"{summary['final_equity']:,.2f}")
    if not equity.empty:
        st.plotly_chart(_paper_equity_figure(equity), width="stretch")
    st.subheader("订单事件")
    st.dataframe(orders, width="stretch", hide_index=True)
    st.subheader("权益事件")
    st.dataframe(equity, width="stretch", hide_index=True)


def _render_data_summary(frame: pd.DataFrame) -> None:
    cols = st.columns(4)
    cols[0].metric("K线数量", str(len(frame)))
    cols[1].metric("起始日期", str(frame.iloc[0]["trading_day"]))
    cols[2].metric("结束日期", str(frame.iloc[-1]["trading_day"]))
    cols[3].metric("最新收盘", f"{frame.iloc[-1]['close_price']:.2f}")


def _load_bars(path: str):
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    try:
        return read_bars_csv(csv_path)
    except Exception as exc:
        st.error(f"读取CSV失败：{exc}")
        return []


def _render_strategy_picker(settings: dict, key_prefix: str):
    specs = discover_strategies()
    if not specs:
        st.error("没有发现可用策略。")
        return None
    labels = [_strategy_label(spec) for spec in specs]
    selected_label = st.selectbox("选择策略", labels, key=f"{key_prefix}_strategy_select")
    spec = specs[labels.index(selected_label)]
    params = {}
    with st.expander("策略参数", expanded=True):
        for param in inspect_strategy_parameters(spec):
            params[param.name] = _render_strategy_param_input(param, settings, key_prefix)
    try:
        return instantiate_strategy(spec, params)
    except Exception as exc:
        st.error(f"策略实例化失败：{exc}")
        return None


def _render_strategy_param_input(param, settings: dict, key_prefix: str):
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


def _strategy_label(spec) -> str:
    source = "内置" if spec.source == "builtin" else "用户"
    return f"{spec.name} ({source})"


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
        figure.add_trace(go.Scatter(x=buys["trading_day"], y=buys["price"], mode="markers", marker={"color": "#16a34a", "size": 10}, name="买入"))
        figure.add_trace(go.Scatter(x=sells["trading_day"], y=sells["price"], mode="markers", marker={"color": "#dc2626", "size": 10}, name="卖出"))
    figure.update_layout(height=430, margin={"l": 10, "r": 10, "t": 30, "b": 10}, xaxis_rangeslider_visible=False)
    return figure


def _signal_figure(bars: pd.DataFrame, signals: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=bars["trading_day"], y=bars["close_price"], mode="lines", name="收盘价"))
    if not signals.empty:
        buys = signals[signals["action"] == "buy"]
        sells = signals[signals["action"] == "sell"]
        figure.add_trace(go.Scatter(x=buys["trading_day"], y=buys["price"], mode="markers", marker={"color": "#16a34a", "size": 10}, name="买入信号"))
        figure.add_trace(go.Scatter(x=sells["trading_day"], y=sells["price"], mode="markers", marker={"color": "#dc2626", "size": 10}, name="卖出信号"))
    figure.update_layout(height=360, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    return figure


def _equity_figure(equity: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=equity["trading_day"], y=equity["equity"], mode="lines", name="权益"))
    figure.add_trace(go.Scatter(x=equity["trading_day"], y=equity["cash"], mode="lines", name="现金"))
    figure.update_layout(height=330, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    return figure


def _paper_equity_figure(equity: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=equity["trading_day"], y=equity["equity"], mode="lines", name="纸面权益"))
    figure.update_layout(height=330, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    return figure


if __name__ == "__main__":
    main()
