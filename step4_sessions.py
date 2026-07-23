"""
STEP 4 — Session management
===========================

Goal: keep conversational context across turns, then resume it later.

Two ways to hold context (know when to pick which — it's a classic exam question):
- ClaudeSDKClient  -> a live, stateful connection. Multiple .query() calls share
  one growing context. Best for chat UIs, REPLs, response-driven logic.
- query(resume=id) -> stateless calls that reattach to a stored session by ID.
  Best for scripts/serverless where you don't hold a process open.

Key ideas (exam-relevant):
- The session_id comes back on ResultMessage (and AssistantMessage). Capture it.
- resume=<id> continues that exact session. fork_session=True branches a COPY so
  you can explore without mutating the original transcript (great for "what if"
  branches, A/B prompts, or parallel exploration from a checkpoint).
- Context management tradeoff: a long single session gives continuity but grows
  the context window (cost + dilution). Forking / new sessions keep contexts lean.
- Do NOT `break` out of the receive_response() iterator early — let it drain, or
  you can hit asyncio cleanup issues.
"""

import asyncio

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    query,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)


async def print_response(client: ClaudeSDKClient) -> str | None:
    """Drain one response; return the session_id seen on the ResultMessage."""
    session_id = None
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[claude] {block.text}")
        elif isinstance(message, ResultMessage):
            session_id = message.session_id
    return session_id


async def main() -> None:
    options = ClaudeAgentOptions(max_turns=4)

    # --- Part A: a live stateful session ---
    async with ClaudeSDKClient(options=options) as client:
        await client.query("My name is Deepak and I'm prepping for the CCA-F exam.")
        session_id = await print_response(client)

        # The model REMEMBERS the previous turn — same session context.
        await client.query("What's my name, and what am I preparing for?")
        await print_response(client)

    print(f"\n[stored session] {session_id}\n")

    # --- Part B: reattach to that session LATER, statelessly ---
    # A fresh process could do exactly this, given the saved session_id.
    async for message in query(
        prompt="Give me one last-minute tip for that exam.",
        options=ClaudeAgentOptions(resume=session_id, max_turns=2),
    ):
        if isinstance(message, ResultMessage):
            print(f"[resumed] {message.result}")

    # --- Part C: fork instead of continue, to branch safely ---
    async for message in query(
        prompt="Actually, rewrite that tip for a total beginner instead.",
        options=ClaudeAgentOptions(resume=session_id, fork_session=True, max_turns=2),
    ):
        if isinstance(message, ResultMessage):
            print(f"[forked branch] {message.result}")
            print(f"[forked branch has a NEW session_id] {message.session_id}")


if __name__ == "__main__":
    asyncio.run(main())
