"""
CAPSTONE — Manual orchestrator with EXPLICIT context passing
============================================================

In step 5 the model decided what context to pass to each subagent. Sometimes you
want to control the boundary yourself — a deterministic pipeline where YOU choose
exactly what crosses from worker A to worker B. That is the orchestrator-worker
pattern, and it's the cleanest way to *see* "passing context between agents".

This capstone combines everything:
  - a custom tool (step 2)
  - two workers, each a fresh isolated query() call (step 5's isolation, done by hand)
  - explicit hand-off: worker A's OUTPUT becomes part of worker B's PROMPT
  - loop-level error handling + guardrails (step 3)

Pipeline:
  research_worker  --(findings text)-->  writer_worker  -->  final brief

Why do it manually instead of agents=+Task?
  - Determinism: the pipeline always runs A then B.
  - Total control of the context boundary: you pass ONLY the findings, nothing else,
    so the writer's context stays minimal (context management + cost control).
  - Easy to test each stage in isolation.
Trade-off: you give up the model's flexibility to choose helpers dynamically.
"""

import asyncio

from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server,
    query,
    ClaudeAgentOptions,
    ResultMessage,
    ClaudeSDKError,
)

# --- a tiny custom tool the researcher can use (self-contained, no network) ---
_FACTS = {
    "agent loop": "Claude reasons, optionally calls a tool, ingests the result, and repeats until done.",
    "subagent": "A specialist that runs in an isolated context window and returns only its final summary.",
    "guardrail": "Bounds like max_turns and max_budget_usd that stop runaway loops.",
}


@tool("fact_lookup", "Look up a short definition for an agent-architecture term.", {"term": str})
async def fact_lookup(args: dict) -> dict:
    term = args["term"].strip().lower()
    hit = _FACTS.get(term)
    if hit is None:
        return {"content": [{"type": "text", "text": f"No entry for {term!r}."}], "is_error": True}
    return {"content": [{"type": "text", "text": hit}]}


kb = create_sdk_mcp_server(name="kb", version="1.0.0", tools=[fact_lookup])


async def run_worker(prompt: str, *, allowed_tools: list[str], system: str) -> str:
    """Run one isolated worker to completion and return its final text.

    Each call is a FRESH session (query() default) — the worker knows nothing
    except what we put in `prompt`. That is the isolation boundary, enforced by us.
    """
    options = ClaudeAgentOptions(
        system_prompt=system,
        mcp_servers={"kb": kb},
        allowed_tools=allowed_tools,
        permission_mode="default",
        max_turns=6,
        max_budget_usd=0.30,
    )
    final: ResultMessage | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            final = message

    if final is None or final.is_error or final.subtype != "success":
        raise RuntimeError(f"Worker failed: {getattr(final, 'subtype', 'no-result')}")
    return final.result or ""


async def main() -> None:
    topic = "how an agentic loop uses subagents and guardrails"

    try:
        # --- Worker A: research. Gets tools, produces raw findings. ---
        findings = await run_worker(
            prompt=(
                f"Research this topic for a one-page brief: {topic}. "
                "Use the fact_lookup tool for the terms 'agent loop', 'subagent', and "
                "'guardrail'. Return only a bulleted list of findings."
            ),
            allowed_tools=["mcp__kb__fact_lookup"],
            system="You are a precise researcher. Output only bullet points.",
        )
        print("=== WORKER A / findings ===")
        print(findings)

        # --- THE HAND-OFF: we explicitly pass ONLY the findings to worker B. ---
        # Worker B has no tools and no memory of A's process — just this text.
        brief = await run_worker(
            prompt=(
                "Turn these research findings into a tight 150-word brief for an "
                f"exam-prep student:\n\n{findings}"
            ),
            allowed_tools=[],  # writer needs no tools -> smaller blast radius
            system="You are an editor. Clear, structured prose. No preamble.",
        )
        print("\n=== WORKER B / final brief ===")
        print(brief)

    except ClaudeSDKError as e:
        print(f"SDK/process error: {e}")
    except RuntimeError as e:
        print(f"Pipeline error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
