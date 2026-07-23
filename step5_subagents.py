"""
STEP 5 — Subagents & context isolation
======================================

Goal: let a lead ("orchestrator") delegate subtasks to specialist subagents.

Why subagents exist (THE exam point):
- Each subagent runs in its OWN, isolated context window. The orchestrator does
  NOT see the subagent's intermediate reasoning or tool spam — only the subagent's
  final summary comes back. This is a CONTEXT-MANAGEMENT tool: it keeps the main
  thread's context clean and focused, and lets you parallelize work.
- You also scope each subagent's TOOLS and MODEL. Give a cheap researcher `haiku`
  + web tools; give a careful reviewer `opus` + read-only tools. This is how you
  control cost and blast radius per role.

How delegation happens here:
- Define subagents in ClaudeAgentOptions.agents = {name: AgentDefinition(...)}.
- The orchestrator invokes them through the built-in `Task` tool. You describe the
  GOAL; the model decides which subagent to spawn and what context to hand it.
- NOTE: AgentDefinition uses camelCase fields (disallowedTools, permissionMode,
  maxTurns) — it maps to the shared wire format. ClaudeAgentOptions uses snake_case.
  Mixing them up raises TypeError, and it's a favorite exam trap.
"""

import asyncio

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)


async def main() -> None:
    options = ClaudeAgentOptions(
        agents={
            "researcher": AgentDefinition(
                description="Gathers factual information on a topic. Use for any information-gathering subtask.",
                prompt=(
                    "You are a research specialist. Gather concise, accurate facts. "
                    "Return a short bulleted list of findings and nothing else."
                ),
                tools=["WebSearch", "Read"],  # scoped tools for this role
                model="haiku",                # cheap model for gathering
            ),
            "reviewer": AgentDefinition(
                description="Critically reviews a draft for accuracy and gaps. Use before finalizing.",
                prompt=(
                    "You are a meticulous reviewer. Point out inaccuracies, missing "
                    "context, and weak claims. Be terse."
                ),
                tools=["Read"],   # read-only: can't modify anything
                model="sonnet",
            ),
        },
        # The orchestrator needs the Task tool to delegate, plus whatever it uses itself.
        allowed_tools=["Task", "WebSearch", "Read"],
        permission_mode="default",
        max_turns=12,
    )

    prompt = (
        "Research the five domains of the Claude Certified Architect – Foundations exam, "
        "then have the reviewer check your summary for gaps before giving me the final list."
    )

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[orchestrator] {block.text}")
                elif isinstance(block, ToolUseBlock) and block.name == "Task":
                    # Watch the orchestrator hand a subtask to a subagent. The
                    # subagent's own turns run in a separate context you don't see here.
                    print(f"[delegate -> subagent] {block.input}")
        elif isinstance(message, ResultMessage):
            print(f"\n[final] {message.result}")


if __name__ == "__main__":
    asyncio.run(main())
