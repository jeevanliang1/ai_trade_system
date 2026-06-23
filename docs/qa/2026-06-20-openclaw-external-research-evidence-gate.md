# OpenClaw External Research Evidence Gate QA

Date: 2026-06-20

## Scope

Validate that OpenClaw-powered fundamental/information-side research is not accepted as verified when it lacks external URL evidence.

## Red Evidence

- `AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_openclaw_external_research_script.py::test_parse_openclaw_agent_output_extracts_web_search_sources_from_session_file -q`
  - Initially failed because `scripts/openclaw_external_research.py` returned only the `openclaw_agent` session source and did not extract `web_search` URLs.
- `AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_system_tools.py::test_batch_fundamental_tool_requires_external_evidence_for_ok_research -q`
  - Initially failed because `research.batch_fundamental` accepted an `ok` OpenClaw summary with no verifiable external URL evidence.

## Green Evidence

- `AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_openclaw_external_research_script.py -q`
  - 4 passed.
- `AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_system_tools.py::test_batch_fundamental_tool_researches_weekly_candidates_with_openclaw tests/test_agent_system_tools.py::test_batch_fundamental_tool_requires_external_evidence_for_ok_research tests/test_agent_system_tools.py::test_weixin_share_tool_prepares_compact_weekly_report_message -q`
  - 3 passed.
- `AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_openclaw_external_research_script.py tests/test_agent_system_tools.py -q`
  - 12 passed.
- `AI_TRADE_LLM_PROVIDER=mock python -m pytest`
  - 257 passed.
- `git diff --check`
  - No whitespace errors.

## Behavior

- OpenClaw session `web_search` results and direct session URL records are parsed for `http://` or `https://` URLs and returned as evidence sources.
- Batch fundamental research downgrades an OpenClaw `ok` result to `failed` with `confidence=low` and `evidence_status=missing_external_evidence` when no URL-backed external source is present.
- The system does not require browser usage; it requires evidence-backed sources for user-facing research conclusions.

## Browser QA

Not applicable. This change affects backend Agent/OpenClaw research evidence handling and docs only; no browser-rendered surface changed.
