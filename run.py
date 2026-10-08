import asyncio
import argparse

from research import ask
import uuid


async def main(question: str, thread: str, chat: bool):
    while True:
        result = await ask(question, thread)
        print(result["answer"])
        print(f"Session: {thread} | Tools: {len(result['trace'])} | Time: {result['elapsed_seconds']}s")
        if not chat:
            return
        question = input("You (/exit to quit): ").strip()
        if question == "/exit":
            return
        while not question:
            question = input("You (/exit to quit): ").strip()
        if question == "/exit":
            return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ask the stock research assistant a question.")
    parser.add_argument("question", nargs="?", default="How has AVANTEL.NS done over the last month?")
    parser.add_argument("--thread", default=uuid.uuid4().hex, help="Reuse an ID to resume a saved conversation.")
    parser.add_argument("--chat", action="store_true", help="Ask follow-up questions interactively.")
    args = parser.parse_args()
    asyncio.run(main(args.question, args.thread, args.chat))
