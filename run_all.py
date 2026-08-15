"""تشغيل خادم Node وبوت Telegram معًا."""
from __future__ import annotations

import atexit
import os
import signal
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
NODE_DIR = ROOT / "node_server"
load_dotenv(ROOT / ".env")

node_process: subprocess.Popen[str] | None = None


def stop_node(*_args):
    global node_process
    if node_process and node_process.poll() is None:
        node_process.terminate()
        try:
            node_process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            node_process.kill()
    node_process = None


def start_node() -> None:
    global node_process
    env = os.environ.copy()
    env["NODE_SERVER_PORT"] = os.getenv("NODE_SERVER_PORT", "3000")
    # يتجنب تعارض منفذ منصة الاستضافة مع منفذ الخادم الداخلي.
    node_process = subprocess.Popen(
        ["npm", "run", "start"],
        cwd=NODE_DIR,
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
        text=True,
    )


def main() -> None:
    signal.signal(signal.SIGINT, stop_node)
    signal.signal(signal.SIGTERM, stop_node)
    atexit.register(stop_node)
    start_node()

    # الاستيراد بعد تحميل البيئة حتى يقرأ bot.py جميع الإعدادات الصحيحة.
    import bot

    try:
        bot.main()
    finally:
        stop_node()


if __name__ == "__main__":
    main()
