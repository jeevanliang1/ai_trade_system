from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GatewayPlan:
    name: str
    market: str
    notes: str
    deployment_hint: str


SUPPORTED_A_SHARE_GATEWAYS = [
    GatewayPlan(
        name="XTP",
        market="A股/ETF期权",
        notes="vn.py 官方列出的中泰 XTP 网关方向，需券商开通接口。",
        deployment_hint="拿到账号后在独立 gateway 配置中接入，策略层不直接依赖 XTP SDK。",
    ),
    GatewayPlan(
        name="TORA",
        market="A股/ETF期权",
        notes="vn.py 官方列出的华鑫奇点网关方向，通常需要 Windows 与券商测试账号。",
        deployment_hint="可将交易网关部署在 Windows，Linux 策略服务通过 RPC/消息联动。",
    ),
    GatewayPlan(
        name="QMT/xtquant",
        market="A股",
        notes="常见个人量化路线，依赖 miniQMT 客户端与券商权限。",
        deployment_hint="预留适配层，先跑模拟交易，后续按券商实际 API 补实现。",
    ),
]
