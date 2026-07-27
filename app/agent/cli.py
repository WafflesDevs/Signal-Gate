"""
CLI chat for Signal Gate.

Run:
  python -m app.agent.cli

Uses the same agent as the website. Make sure FastAPI is running on :8000
so MCP tools can hit /paper and /price.
"""

import asyncio

from dotenv import load_dotenv

from app.agent.agent_service import resume_turn, run_turn

load_dotenv()


async def main():
    # Same thread_id = same conversation memory for this CLI run
    thread_id = "signal-gate-cli"

    print("----SIGNAL GATE----")
    print("Chat started. Type 'quit' or 'exit' to stop.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Bye.")
            break

        # 1) Send the message to the agent
        result = await run_turn(thread_id, user_input)

        # 2) If it wants to buy/sell, ask you y/n, then resume
        while result.get("pending_trades"):
            decisions = []
            for action in result["pending_trades"]:
                print(f"\nPending trade: {action['name']} {action['arguments']}")
                choice = input("Approve this trade? (y/n): ").strip().lower()

                if choice == "y" or choice == "yes":
                    decisions.append({"type": "approve"})
                else:
                    decisions.append(
                        {
                            "type": "reject",
                            "message": "User said no. Do not retry this trade.",
                        }
                    )

            result = await resume_turn(thread_id, decisions)

        # 3) Print the final reply
        print("Assistant:", result.get("reply", ""))
        print()


if __name__ == "__main__":
    asyncio.run(main())
