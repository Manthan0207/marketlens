"""Persistent sessions and bounded agent execution."""
import time
from pathlib import Path
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from graph import build_graph

DB_PATH = Path(__file__).parent / "data" / "conversations.sqlite"


async def ask(question, thread_id, db_path=DB_PATH):
    if not question.strip() or not thread_id.strip():
        raise ValueError("Question and thread ID must not be empty.")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        graph = await build_graph(checkpointer=saver)
        trace, answer = [], ""
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 12}
        async for update in graph.astream({"messages": [HumanMessage(question)]}, config, stream_mode="updates"):
            for node, payload in update.items():
                for message in payload.get("messages", []):
                    for call in getattr(message, "tool_calls", []):
                        trace.append({"tool": call["name"], "arguments": call["args"]})
                    if node == "agent" and not getattr(message, "tool_calls", []):
                        answer = message.content
        return {"answer": answer, "trace": trace, "elapsed_seconds": round(time.perf_counter() - started, 2)}


async def history(thread_id, db_path=DB_PATH):
    if not db_path.exists():
        return []
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        checkpoint = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})
        messages = checkpoint.checkpoint["channel_values"].get("messages", []) if checkpoint else []
        return [{"role": "user" if message.type == "human" else "assistant", "content": message.content}
                for message in messages if message.type == "human" or
                (message.type == "ai" and not getattr(message, "tool_calls", []))]
