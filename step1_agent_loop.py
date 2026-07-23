"""
STEP 1 — The agentic loop with built-in tools
==============================================

Goal: see the full loop run end to end using query() (the stateless entry point).

Key ideas (exam-relevant):
- query() creates a FRESH session each call. No memory between calls unless you
  pass resume=/continue_conversation=. Great for one-off tasks.
- The SDK runs the loop: Claude thinks -> may call a tool -> SDK executes it ->
  result is fed back -> repeat until Claude produces a final answer.
- allowed_tools does NOT restrict Claude to only those tools. It AUTO-APPROVES
  them (no permission prompt). Unlisted tools fall through to permission_mode.
  To actually block a tool, use disallowed_tools.
- Always terminate the loop safely with max_turns (a hard cap on tool round-trips).
"""

import asyncio

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)


async def main() -> None:
    options = ClaudeAgentOptions(
        # Built-in Claude Code tools. These are AVAILABLE by default; listing them
        # here just means "don't stop to ask permission for these".
        allowed_tools=["Read", "Glob", "Grep"],
        # Read-only task, so no edits needed. 'default' would prompt on writes.
        permission_mode="default",
        # Guardrail: never loop more than 8 tool round-trips.
        max_turns=8,
        # Optional cost ceiling (client-side estimate).
        max_budget_usd=0.50,
    )

    prompt = "List the Python files in the current directory and summarize what this project does."

    async for message in query(prompt=prompt, options=options):
        # --- Assistant turns: text the model wrote + tools it decided to call ---
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[claude] {block.text}")
                elif isinstance(block, ToolUseBlock):
                    # This is the model DECIDING to call a tool. The SDK will run
                    # it and feed the result back into the loop automatically.
                    print(f"[tool-call] {block.name}({block.input})")

        # --- The terminal message of the whole loop ---
        elif isinstance(message, ResultMessage):
            print("\n=== loop finished ===")
            print(f"subtype     : {message.subtype}")       # 'success' if all good
            print(f"turns       : {message.num_turns}")
            print(f"cost (usd)  : {message.total_cost_usd}")
            print(f"session_id  : {message.session_id}")     # you'll reuse this in step 4
            print(f"final answer:\n{message.result}")


if __name__ == "__main__":
    asyncio.run(main())
