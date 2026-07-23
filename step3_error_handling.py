"""
STEP 3 — Error handling, guardrails, and retries
================================================

Goal: make a run production-safe. There are THREE layers of failure to handle,
and the exam expects you to know which is which:

  1. PROCESS/CONNECTION errors  -> the CLI isn't installed, crashes, or emits bad
     JSON. These RAISE Python exceptions (subclasses of ClaudeSDKError). Catch them.
  2. LOOP-level outcomes        -> the loop ran but ended badly: hit max_turns, hit
     the budget, or the final API call errored. These DON'T raise; they arrive as a
     ResultMessage whose `subtype` / `is_error` you must INSPECT.
  3. TOOL-level errors          -> handled inside the tool (step 2), returned as data.

Key ideas (exam-relevant):
- Guardrails are design, not an afterthought: max_turns bounds infinite tool loops,
  max_budget_usd bounds cost, permission_mode bounds blast radius.
- fallback_model gives graceful degradation if the primary model errors.
- Distinguish "the loop failed" (subtype starts with 'error_') from
  "the loop succeeded but the last API call errored" (subtype='success' AND is_error=True).
"""

import asyncio

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    TextBlock,
    ClaudeSDKError,  # base class for all SDK errors
)

# Specific subclasses exist (CLINotFoundError, ProcessError, CLIJSONDecodeError),
# but names can vary by version, so fall back to the base class if import fails.
try:
    from claude_agent_sdk import CLINotFoundError, ProcessError, CLIJSONDecodeError
except ImportError:  # pragma: no cover
    CLINotFoundError = ProcessError = CLIJSONDecodeError = ClaudeSDKError


async def run_once(prompt: str) -> ResultMessage | None:
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob"],
        permission_mode="default",
        max_turns=5,             # guardrail: bound the loop
        max_budget_usd=0.25,     # guardrail: bound the cost
        model="sonnet",
        fallback_model="haiku",  # graceful degradation if primary errors
    )

    final: ResultMessage | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[claude] {block.text}")
        elif isinstance(message, ResultMessage):
            final = message
    return final


def classify(result: ResultMessage) -> str:
    """Turn a ResultMessage into a human-readable outcome (LAYER 2)."""
    if result.subtype == "success" and not result.is_error:
        return f"OK: {result.result}"
    if result.subtype == "success" and result.is_error:
        # Loop completed but the final model request failed.
        return f"PARTIAL: final API call failed (status={result.api_error_status})"
    if result.subtype == "error_max_turns":
        return "STOPPED: hit max_turns — task too complex for the turn budget."
    if result.subtype == "error_max_budget_usd":
        return "STOPPED: hit the cost ceiling."
    return f"ERROR: {result.subtype} ({result.errors})"


async def main() -> None:
    try:  # LAYER 1: catch process/connection failures
        result = await run_once("Summarize the README in this directory.")
    except CLINotFoundError:
        print("Claude Code CLI not found. Run: npm i -g @anthropic-ai/claude-code")
        return
    except (ProcessError, CLIJSONDecodeError) as e:
        print(f"CLI process problem: {e}")
        return
    except ClaudeSDKError as e:
        print(f"SDK error: {e}")
        return

    if result is None:
        print("No result message received — unexpected.")
        return

    print("\n" + classify(result))  # LAYER 2


if __name__ == "__main__":
    asyncio.run(main())
