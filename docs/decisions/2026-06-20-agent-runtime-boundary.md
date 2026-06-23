# Agent Runtime Boundary

Date: 2026-06-20

## Decision

Keep `ai_trade_system.agent` as the local Agent kernel for the next iteration, and do not embed a broad open-source Agent runtime yet.

The current kernel already owns the project-specific parts that must stay deterministic and auditable:

- tool registry and permission levels
- durable task/step/report persistence
- OpenClaw/MCP/Weixin entry boundary
- local trading-system service adapters
- live-trading request blocking
- React AI command-center visibility

The next Agent expansion should add repo-local memory/skill management and richer planning policy around this kernel. If graph-state orchestration becomes necessary after that, evaluate LangGraph as an adapter around the existing tool registry rather than replacing the kernel. Avoid introducing AutoGen/CrewAI-style multi-agent runtimes until there is a concrete need for multi-role collaboration beyond tool planning.

## Rationale

This system needs traceability, permission gates, and trading-specific safety more than generic autonomous-agent breadth. A large external runtime would add another state model and permission surface before the system has a stable memory/skill UI. Keeping the kernel local lets OpenClaw remain the external computer/browser operator while `ai_trade_system` remains the owner of trading data, risk boundaries, reports, and front-end status.

## Follow-Up

- Add a Memory/Skill management page for reusable Agent instructions, allowed tools, prompt templates, and approval policy.
- Extend planner state so a task can explain why each next step was selected.
- Re-evaluate LangGraph only when tasks need branching, retries, or long-running graph checkpoints that the current sequential orchestrator cannot express cleanly.
