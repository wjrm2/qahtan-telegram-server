from pathlib import Path

ROOT = Path(__file__).parent
BOT = (ROOT / "bot.py").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/run-bot.yml").read_text(encoding="utf-8")


def test_webapp_uses_reply_keyboard_and_https_guard():
    assert "KeyboardButton" in BOT
    assert "ReplyKeyboardMarkup" in BOT
    assert "web_app=WebAppInfo" in BOT
    assert 'webapp_url.startswith("https://")' in BOT


def test_webapp_data_handler_is_registered():
    assert "async def webapp_data_handler" in BOT
    assert "filters.StatusUpdate.WEB_APP_DATA" in BOT
    assert "allowed_actions" in BOT


def test_workflow_passes_webapp_url_without_secret_in_source():
    assert "AZ_WEBAPP_URL: ${{ vars.AZ_WEBAPP_URL }}" in WORKFLOW
    assert "AZ_WEBAPP_URL: ${{ secrets" not in WORKFLOW
