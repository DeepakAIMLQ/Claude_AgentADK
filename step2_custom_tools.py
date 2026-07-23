"""
STEP 2 — Custom tools with @tool + an in-process MCP server
===========================================================

Goal: give the agent a capability the built-in tools don't cover, and make the
TOOL ITSELF robust (tool-level error handling belongs here, not in the loop).

Key ideas (exam-relevant):
- A custom tool is just an async function wrapped by @tool(name, desc, schema).
- create_sdk_mcp_server() bundles tools into an IN-PROCESS MCP server. "In-process"
  = runs inside your Python program, no subprocess, no network. Fast + simple.
- Naming: a tool on server key "biz" named "lookup_order" is referenced as
  mcp__biz__lookup_order  (pattern: mcp__<serverKey>__<toolName>).
- TOOL DESIGN is a whole exam domain. Good tools: narrow purpose, clear
  description (the model routes on the description!), typed inputs, and they
  RETURN errors as data instead of raising — so the model can recover.
"""

import asyncio

from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server,
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)

# A fake "database" so the example is self-contained.
_ORDERS = {
    "A100": {"status": "shipped", "eta_days": 2},
    "A101": {"status": "processing", "eta_days": 5},
}


@tool(
    "lookup_order",
    # This description is how the model decides WHEN to call the tool. Be precise.
    "Look up the shipping status and ETA of a customer order by its order ID.",
    {"order_id": str},  # simple type mapping; the SDK builds the JSON schema
)
async def lookup_order(args: dict) -> dict:
    order_id = args["order_id"].strip().upper()

    # Tool-level error handling: return an error RESULT, don't raise.
    # Returning is_error=True lets Claude read the message and react/retry
    # rather than the whole loop crashing.
    if order_id not in _ORDERS:
        return {
            "content": [{"type": "text", "text": f"No order found with ID {order_id!r}."}],
            "is_error": True,
        }

    o = _ORDERS[order_id]
    return {
        "content": [
            {"type": "text", "text": f"Order {order_id}: {o['status']}, ETA {o['eta_days']} days."}
        ]
    }


# Bundle the tool(s) into an in-process MCP server.
support_server = create_sdk_mcp_server(
    name="support",
    version="1.0.0",
    tools=[lookup_order],
)


async def main() -> None:
    options = ClaudeAgentOptions(
        mcp_servers={"support": support_server},         # key "support" -> prefix mcp__support__
        allowed_tools=["mcp__support__lookup_order"],     # auto-approve our tool
        max_turns=6,
    )

    async for message in query(
        prompt="A customer is asking about order A101 and order Z999. Give them both statuses.",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[claude] {block.text}")
        elif isinstance(message, ResultMessage):
            print(f"\n[result] {message.result}")


if __name__ == "__main__":
    asyncio.run(main())
