import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from research import ask, history


@tool
def fixture_prices() -> str:
    """Return a known offline fixture."""
    return "Fixture return: 8%"


class FakeModel:
    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        if messages[-1].type == "tool":
            return AIMessage(content="Fixture return: 8%")
        return AIMessage(content="", tool_calls=[{"name": "fixture_prices", "args": {}, "id": "fixture-call"}])


class ResearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_loop_trace_and_session_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "sessions.sqlite"
            with patch.dict(os.environ, {"HF_TOKEN": "test"}), patch("graph.ChatOpenAI", return_value=FakeModel()), patch("graph.MultiServerMCPClient") as client:
                client.return_value.get_tools = AsyncMock(return_value=[fixture_prices])
                result = await ask("How did the fixture perform?", "session-a", db)
                self.assertEqual(result["answer"], "Fixture return: 8%")
                self.assertEqual(result["trace"][0]["tool"], "fixture_prices")
                await ask("Follow up", "session-a", db)
            # A new SQLite connection loads the same conversation, with isolated IDs.
            saved = await history("session-a", db)
            self.assertEqual(len(saved), 4)
            self.assertEqual(saved[0]["role"], "user")
            self.assertEqual(await history("session-b", db), [])

    async def test_empty_question_rejected(self):
        with self.assertRaises(ValueError):
            await ask(" ", "session")
