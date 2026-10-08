import asyncio
import sys
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

HERE = Path(__file__).parent

load_dotenv(HERE / ".env")

async def main():
    # Initialize the client inside an async function
    clients = MultiServerMCPClient({
        "stocks": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(HERE / "custom_mcp.py")],
        },
    })

    tools = await clients.get_tools()
    for tool in tools:
        print(f"{tool.name}: {tool.description}")
    return tools

# Execute the asynchronous event loop
if __name__ == "__main__":
    asyncio.run(main())
