from datetime import date
import warnings

from ai_trade_system.indicators import IndicatorSnapshot
from ai_trade_system.llm import DeepSeekLLMProvider, LLMResearchRequest, MockLLMProvider, build_research_prompt, provider_from_env


def _snapshot():
    return IndicatorSnapshot(
        symbol="000001",
        trading_day=date(2024, 1, 5),
        close_price=12.0,
        short_ma=11.0,
        long_ma=10.0,
        rsi=55.0,
        momentum=9.0,
        drawdown_pct=-3.0,
        trend="bullish",
    )


def test_build_research_prompt_contains_technical_and_information_inputs():
    request = LLMResearchRequest(
        symbol="000001",
        horizon="5个交易日",
        indicator_snapshot=_snapshot(),
        information_notes=["政策支持流动性改善"],
        risk_context={"max_drawdown_pct": 20},
        prompt_mode="balanced",
    )

    prompt = build_research_prompt(request)

    assert "技术指标" in prompt
    assert "信息面" in prompt
    assert "政策支持流动性改善" in prompt


def test_mock_llm_provider_returns_structured_bullish_insight():
    request = LLMResearchRequest(
        symbol="000001",
        horizon="5个交易日",
        indicator_snapshot=_snapshot(),
        information_notes=["政策支持流动性改善"],
        risk_context={"max_drawdown_pct": 20},
        prompt_mode="balanced",
    )

    insight = MockLLMProvider().generate_insight(request)

    assert insight.direction == "bullish"
    assert insight.confidence >= 70
    assert insight.provider == "MockLLMProvider"


def test_mock_llm_provider_uses_timezone_aware_created_at_without_deprecation_warning():
    request = LLMResearchRequest(
        symbol="000001",
        horizon="5个交易日",
        indicator_snapshot=_snapshot(),
        information_notes=[],
        risk_context={},
        prompt_mode="balanced",
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        insight = MockLLMProvider().generate_insight(request)

    assert insight.created_at.endswith("Z")


def test_deepseek_llm_provider_maps_json_response_to_insight():
    class FakeClient:
        def chat_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> dict:
            assert "JSON" in system_prompt
            assert "技术指标" in user_prompt
            return {
                "status": "ok",
                "provider": "deepseek",
                "data": {
                    "direction": "bullish",
                    "confidence": 81,
                    "suggested_action": "hold",
                    "technical_evidence": ["趋势向上"],
                    "information_evidence": ["订单改善"],
                    "risk_warnings": ["不追高"],
                },
            }

    request = LLMResearchRequest(
        symbol="000001",
        horizon="5个交易日",
        indicator_snapshot=_snapshot(),
        information_notes=["订单改善"],
        risk_context={"max_drawdown_pct": 20},
        prompt_mode="balanced",
    )

    insight = DeepSeekLLMProvider(client=FakeClient()).generate_insight(request)

    assert insight.provider == "DeepSeekLLMProvider"
    assert insight.direction == "bullish"
    assert insight.confidence == 81
    assert insight.technical_evidence == ["趋势向上"]


def test_provider_from_env_uses_deepseek_when_configured(monkeypatch):
    monkeypatch.setenv("AI_TRADE_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret")

    provider = provider_from_env()

    assert isinstance(provider, DeepSeekLLMProvider)
