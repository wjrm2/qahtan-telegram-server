import unittest
from pathlib import Path

ROOT = Path(__file__).parent
BOT = (ROOT / "bot.py").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/run-bot.yml").read_text(encoding="utf-8")


class WebAppDetachTests(unittest.TestCase):
    def test_webapp_is_detached_from_bot_menu_and_handlers(self):
        self.assertIn("def main_menu_markup", BOT)
        self.assertNotIn("WebAppInfo", BOT)
        self.assertNotIn("web_app=", BOT)
        self.assertNotIn("async def webapp_data_handler", BOT)
        self.assertNotIn("filters.StatusUpdate.WEB_APP_DATA", BOT)
        self.assertNotIn("فتح لوحة عز الحديثة", BOT)

    def test_workflow_does_not_pass_webapp_url_to_bot(self):
        self.assertNotIn("AZ_WEBAPP_URL", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
