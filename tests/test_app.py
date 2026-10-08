import unittest
import os
from pathlib import Path
from streamlit.testing.v1 import AppTest


class DashboardTests(unittest.TestCase):
    def test_live_lookup_displays_provider_failure(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {"HF_TOKEN": ""}), patch("custom_mcp.get_stock_data", return_value={"error": "Fixture provider failure"}):
            app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=30).run()
            app.radio[0].set_value("Live research").run()
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn("Fixture provider failure", app.error[0].value)

    def test_offline_demo_renders_without_provider_calls(self):
        from unittest.mock import patch
        with patch("custom_mcp.get_stock_data", side_effect=AssertionError("Unexpected network lookup")):
            app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 4)
        self.assertIn("synthetic", app.info[0].value.lower())
        self.assertEqual(app.metric[1].label, "Observed return")
