# Agent SDK Lab — CCA-F oriented

A hands-on, step-by-step lab for the **Claude Agent SDK** (Python), built to
double as prep for the **Claude Certified Architect – Foundations (CCA-F)** exam.
Each file isolates one architectural concept and comments the *design tradeoffs*
the exam actually asks about (it is closed-book and scenario-based, so the "why"
matters more than the syntax).

## Prerequisites (one-time)

```bash
# 1. Node + Claude Code CLI (the SDK runs on top of it)
npm install -g @anthropic-ai/claude-code

# 2. Python 3.10+ and the SDK, in a virtualenv
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install claude-agent-sdk

# 3. Auth
export ANTHROPIC_API_KEY=sk-ant-...   # from console.anthropic.com
```

## Run order

| Step | File | Concept | CCA-F domain |
|------|------|---------|--------------|
| 1 | `step1_agent_loop.py`   | The agentic loop + built-in tools | Agentic Architecture |
| 2 | `step2_custom_tools.py` | `@tool` + in-process MCP server   | Tool Design & MCP |
| 3 | `step3_error_handling.py` | Loop errors, guardrails, retries | Agentic Architecture |
| 4 | `step4_sessions.py`     | `ClaudeSDKClient`, resume, forking | Context Management |
| 5 | `step5_subagents.py`    | Subagents + context isolation      | Agentic Architecture / Context Mgmt |
| 6 | `capstone_orchestrator.py` | Manual orchestrator-worker pipeline | all of the above |

```bash
python step1_agent_loop.py
```

## The one mental model to hold

An "agent" here is a **loop**, not a single call:

```
prompt --> [ Claude decides ] --> tool call? --yes--> run tool --> feed result back --+
                  ^                                                                    |
                  |------------------------------ no (final answer) <------------------+
```

The SDK owns that loop for you. Your job as an architect is to shape four things
around it: which **tools** it can reach, how you **handle failure**, how you
manage **context** (sessions + subagents), and where you put **guardrails**
(`max_turns`, `max_budget_usd`, permissions).
