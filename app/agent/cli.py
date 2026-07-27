"""
CLI chat for Signal Gate.

Run:
  python -m app.agent.cli

Website chat passes the authenticated user id so trades use Settings-linked
Alpaca keys. This CLI has no login — portfolio/trading tools will refuse
with "Link Alpaca in Settings" / login required (no .env Alpaca fallback).
"""

import asyncio

from dotenv import load_dotenv

from app.agent.agent_service import resume_turn, run_turn

load_dotenv()


async def main():
    # Same thread_id = same conversation memory for this CLI run
    thread_id = "signal-gate-cli"

    print("----SIGNAL GATE----")
    print(
        "CLI has no user session — trading tools will not use .env Alpaca keys.\n"
        "Use the website Chat (logged in + Settings linked) to place trades.\n"
    )
    print("Chat started. Type 'quit' or 'exit' to stop.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Bye.")
            break

        # No user_id — tools fail clearly instead of using project .env keys
        result = await run_turn(thread_id, user_input, user_id=None)

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

            result = await resume_turn(thread_id, decisions, user_id=None)

        print("Assistant:", result.get("reply", ""))
        print()


if __name__ == "__main__":
    asyncio.run(main())
