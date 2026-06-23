# 2026-06-21 科创板/创业板缠论多级别日线锚定扫描

## 扫描结论

- 策略：`chan_multilevel_daily_anchor`，即当前默认扫描策略“缠论多级别日线锚定”。参数：`min_bars=60`，`lookback=120`，按正向买入信号 `total_score` 降序排序。
- 行情请求截止：`2026-06-19`；AKShare 本轮实际可用最新交易日主要为 `2026-06-18`。
- 覆盖：科创板 `608` 只，创业板 `1398` 只，合计 `2006` 只；两板均已生成本地 `qfq daily` 文件并完成扫描。
- 科创板：买入候选 `224` 只，风险/卖出信号 `171` 只，样本不足 `6` 只，行情滞后 `3` 只。
- 创业板：买入候选 `314` 只，风险/卖出信号 `636` 只，样本不足 `8` 只，行情滞后 `3` 只。
- 完整结果：`logs/radar/weekly_star_chinext_chan_daily_anchor_scan_20260621.csv`；结构化摘要：`logs/radar/weekly_star_chinext_chan_daily_anchor_scan_20260621.json`。

## 非 ST 综合观察榜

| 排名 | 代码 | 名称 | 分数 | 最新日 | 收盘 | 信号 | 核心理由 |
| --- | --- | --- | ---: | --- | ---: | --- | --- |
| 1 | 688807 | 优迅股份 | 94.0 | 2026-06-18 | 449.80 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 2 | 688671 | 碧兴物联 | 94.0 | 2026-06-18 | 30.78 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 3 | 688531 | 日联科技 | 94.0 | 2026-06-18 | 181.88 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 4 | 688512 | 慧智微 | 94.0 | 2026-06-18 | 15.23 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 5 | 688331 | 荣昌生物 | 94.0 | 2026-06-18 | 114.48 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 6 | 688081 | 兴图新科 | 94.0 | 2026-06-18 | 49.33 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 7 | 688001 | 华兴源创 | 94.0 | 2026-06-18 | 81.09 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 8 | 301588 | 美新科技 | 94.0 | 2026-06-18 | 41.14 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 9 | 301372 | 科净源 | 94.0 | 2026-06-18 | 34.84 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 10 | 301345 | 涛涛车业 | 94.0 | 2026-06-18 | 204.38 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 11 | 301172 | 君逸数码 | 94.0 | 2026-06-18 | 31.81 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 12 | 301150 | 中一科技 | 94.0 | 2026-06-18 | 63.98 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 13 | 300964 | 本川智能 | 94.0 | 2026-06-18 | 115.25 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 14 | 300939 | 秋田微 | 94.0 | 2026-06-18 | 69.82 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 15 | 300931 | 通用电梯 | 94.0 | 2026-06-18 | 16.25 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 16 | 300872 | 天阳科技 | 94.0 | 2026-06-18 | 19.63 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 17 | 300843 | 胜蓝股份 | 94.0 | 2026-06-18 | 126.80 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 18 | 300632 | 光莆股份 | 94.0 | 2026-06-18 | 31.48 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 19 | 300540 | 蜀道装备 | 94.0 | 2026-06-18 | 25.33 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 20 | 300432 | 富临精工 | 94.0 | 2026-06-18 | 22.86 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |

## 科创板非 ST 观察榜

| 排名 | 代码 | 名称 | 分数 | 最新日 | 收盘 | 信号 | 核心理由 |
| --- | --- | --- | ---: | --- | ---: | --- | --- |
| 1 | 688807 | 优迅股份 | 94.0 | 2026-06-18 | 449.80 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 2 | 688671 | 碧兴物联 | 94.0 | 2026-06-18 | 30.78 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 3 | 688531 | 日联科技 | 94.0 | 2026-06-18 | 181.88 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 4 | 688512 | 慧智微 | 94.0 | 2026-06-18 | 15.23 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 5 | 688331 | 荣昌生物 | 94.0 | 2026-06-18 | 114.48 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 6 | 688081 | 兴图新科 | 94.0 | 2026-06-18 | 49.33 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 7 | 688001 | 华兴源创 | 94.0 | 2026-06-18 | 81.09 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 8 | 688981 | 中芯国际 | 78.0 | 2026-06-18 | 140.70 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T2:回落低点抬高后重新向上修复，层级 fractal，关系... |
| 9 | 688818 | 电科蓝天 | 78.0 | 2026-06-18 | 69.80 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T2:回落低点抬高后重新向上修复，层级 fractal，关系... |
| 10 | 688809 | 强一股份 | 78.0 | 2026-06-18 | 626.00 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T2:回落低点抬高后重新向上修复，层级 fractal，关系... |
| 11 | 688802 | 沐曦股份 | 78.0 | 2026-06-18 | 769.89 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T2:回落低点抬高后重新向上修复，层级 fractal，关系... |
| 12 | 688799 | 华纳药厂 | 78.0 | 2026-06-18 | 47.92 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T2:回落低点抬高后重新向上修复，层级 fractal，关系... |
| 13 | 688796 | 百奥赛图 | 78.0 | 2026-06-18 | 94.15 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T2:回落低点抬高后重新向上修复，层级 fractal，关系... |
| 14 | 688795 | 摩尔线程 | 78.0 | 2026-06-18 | 669.00 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T2:回落低点抬高后重新向上修复，层级 fractal，关系... |
| 15 | 688790 | 昂瑞微 | 78.0 | 2026-06-18 | 133.51 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T2:回落低点抬高后重新向上修复，层级 fractal，关系... |

## 创业板非 ST 观察榜

| 排名 | 代码 | 名称 | 分数 | 最新日 | 收盘 | 信号 | 核心理由 |
| --- | --- | --- | ---: | --- | ---: | --- | --- |
| 1 | 301588 | 美新科技 | 94.0 | 2026-06-18 | 41.14 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 2 | 301372 | 科净源 | 94.0 | 2026-06-18 | 34.84 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 3 | 301345 | 涛涛车业 | 94.0 | 2026-06-18 | 204.38 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 4 | 301172 | 君逸数码 | 94.0 | 2026-06-18 | 31.81 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 5 | 301150 | 中一科技 | 94.0 | 2026-06-18 | 63.98 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 6 | 300964 | 本川智能 | 94.0 | 2026-06-18 | 115.25 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 7 | 300939 | 秋田微 | 94.0 | 2026-06-18 | 69.82 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 8 | 300931 | 通用电梯 | 94.0 | 2026-06-18 | 16.25 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 9 | 300872 | 天阳科技 | 94.0 | 2026-06-18 | 19.63 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 10 | 300843 | 胜蓝股份 | 94.0 | 2026-06-18 | 126.80 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 11 | 300632 | 光莆股份 | 94.0 | 2026-06-18 | 31.48 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 12 | 300540 | 蜀道装备 | 94.0 | 2026-06-18 | 25.33 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 13 | 300432 | 富临精工 | 94.0 | 2026-06-18 | 22.86 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T3:向上离开中枢后的回抽未跌回中枢上沿，层级 stroke... |
| 14 | 301678 | 新恒汇 | 78.0 | 2026-06-18 | 64.05 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T2:回落低点抬高后重新向上修复，层级 fractal，关系... |
| 15 | 301630 | 同宇新材 | 78.0 | 2026-06-18 | 402.31 | 缠论多级别日线锚定买入 | chan_multilevel:DAILY_ANCHOR:chan_structure:CHAN_STRUCT_BUY_T2:回落低点抬高后重新向上修复，层级 fractal，关系... |

## 数据滞后样本

### 科创板

| 代码 | 名称 | 最新日 | K线数 | 状态 |
| --- | --- | --- | ---: | --- |
| 688143 | 长盈通 | 2026-06-16 | 715 | scanned |
| 688689 | 银河微电 | 2026-06-11 | 721 | blocked |
| 688121 | 卓然股份 | 2026-04-30 | 694 | risk_signal |

### 创业板

| 代码 | 名称 | 最新日 | K线数 | 状态 |
| --- | --- | --- | ---: | --- |
| 300313 | *ST天山 | 2026-06-17 | 721 | scanned |
| 300159 | *ST新研 | 2026-06-17 | 722 | blocked |
| 300665 | 飞鹿股份 | 2026-06-15 | 721 | blocked |

## 样本不足样本

### 科创板

| 代码 | 名称 | 最新日 | K线数 | 阻断 |
| --- | --- | --- | ---: | --- |
| 688635 | 长进光子 | 2026-06-18 | 17 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 17 根 |
| 688781 | 视涯科技 | 2026-06-18 | 58 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 58 根 |
| 688808 | 联讯仪器 | 2026-06-18 | 37 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 37 根 |
| 688811 | 有研复材 | 2026-06-18 | 47 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 47 根 |
| 688813 | 泰金新能 | 2026-06-18 | 54 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 54 根 |
| 688820 | 盛合晶微 | 2026-06-18 | 40 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 40 根 |

### 创业板

| 代码 | 名称 | 最新日 | K线数 | 阻断 |
| --- | --- | --- | ---: | --- |
| 301513 | 尚水智能 | 2026-06-18 | 42 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 42 根 |
| 301531 | 春光集团 | 2026-06-18 | 29 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 29 根 |
| 301599 | 理奇智能 | 2026-06-18 | 33 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 33 根 |
| 301666 | 大普微-UW | 2026-06-18 | 40 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 40 根 |
| 301669 | C高特电子 | 2026-06-18 | 8 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 8 根 |
| 301682 | 宏明电子 | 2026-06-18 | 58 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 58 根 |
| 301683 | 慧谷新材 | 2026-06-18 | 53 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 53 根 |
| 301696 | 三瑞智能 | 2026-06-18 | 47 | INSUFFICIENT_BARS:至少需要 60 根K线，当前 47 根 |

## 执行证据

- 补数日志：`logs/radar/weekly_board_update_20260621_serial.jsonl`、`logs/radar/weekly_board_update_20260621_spawn.jsonl`。
- 初次线程并发补数触发 `libmini_racer` native 崩溃，后续改用 `spawn` 多进程补数；本次 `spawn` 补数结果为 `updated=1358`、`skipped=3`、`error=0`。
- 扫描耗时：`12.71` 秒。

## 说明

本报告是策略扫描结果，不是投资建议。非 ST 观察榜用于减少高风险标的干扰；完整 CSV 仍保留 ST、风险信号、阻断信号与样本不足标的，便于复查。
