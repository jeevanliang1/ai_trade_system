# AI Command Center DeepSeek Upgrade Design

## Goal

Upgrade the AI Command Center from a synchronous rule-planned MVP into a local AI command hub that can use DeepSeek for structured planning/research, expose background task progress to the React page, and keep OpenClaw/Weixin/MCP as audited trigger sources.

## External API Source

DeepSeek is integrated through its official OpenAI-compatible Chat Completions API:

- Base URL: `https://api.deepseek.com`
- Auth: `Authorization: Bearer $DEEPSEEK_API_KEY`
- Models: `deepseek-v4-flash` by default, configurable to `deepseek-v4-pro`
- Structured responses: `response_format={"type":"json_object"}` with explicit JSON instructions

Secrets are read from environment variables or local `.env.local`. The repository only stores `.env.example`.

## Architecture

1. Add a small DeepSeek client that performs OpenAI-compatible REST requests with `requests`, parses JSON responses, and reports not-configured/failed states without leaking API keys.
2. Add DeepSeek-backed provider behavior to the existing AI Researcher path. If `AI_TRADE_LLM_PROVIDER=deepseek` and a key exists, research uses DeepSeek JSON output; otherwise it falls back to `MockLLMProvider`.
3. Add an Agent planner that asks DeepSeek for a bounded tool plan. The output is normalized against the local tool registry so unknown or unsafe tool names are ignored.
4. Refactor Agent orchestration into resumable execution. Confirm-level tools pause with a pending confirmation, and approval resumes the remaining plan.
5. Add a background task queue for FastAPI-created tasks. The UI receives the task immediately, then polls persisted task state.

## Permission Boundary

DeepSeek can plan and summarize, but it never gets direct broker access. Local tools remain the only execution path. Live trading and brokerage intent remains blocked. Confirm-level tools pause until approved.

## Testing

- DeepSeek client tests use fake HTTP sessions; no real API calls or real secrets.
- Agent tests verify pause/resume and plan normalization.
- API tests verify task creation returns a queued/running task and later persisted state is readable.
- Frontend tests verify queued/waiting states and approval controls remain visible.
