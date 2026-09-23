#!/usr/bin/env python3
"""Send a Telegram message through your own notify bot.

Reads NOTIFY_TELEGRAM_TOKEN and NOTIFY_TELEGRAM_CHAT_ID from the process
environment. stdlib only (urllib) -> no pip install, runs on Windows, macOS
and Linux. The token is never printed or logged: it is only read into memory
and placed in the request URL.

Usage:
    python send_telegram.py "your message"
    echo "your message" | python send_telegram.py -        # read from stdin
    python send_telegram.py --html "<b>bold</b>"            # HTML parse mode
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

TOKEN_KEY = "NOTIFY_TELEGRAM_TOKEN"
CHAT_KEY = "NOTIFY_TELEGRAM_CHAT_ID"
TIMEOUT_SECONDS = 15
MAX_MESSAGE_CHARS = 4096  # Telegram's hard limit for one message
TOKEN_PATTERN = re.compile(r"\d+:[A-Za-z0-9_-]+")
CHAT_ID_PATTERN = re.compile(r"-?\d+|@\w+")


def load_credentials() -> tuple[str, str]:
    """Return (token, chat_id) from the environment, or exit with a clear error."""
    token = os.environ.get(TOKEN_KEY, "").strip()
    chat_id = os.environ.get(CHAT_KEY, "").strip()
    missing = [key for key, value in ((TOKEN_KEY, token), (CHAT_KEY, chat_id)) if not value]
    if missing:
        sys.exit(
            f"error: missing environment variable(s): {', '.join(missing)}. "
            "See the notify skill's SKILL.md, section 'One-time setup'."
        )
    # Validate before the token reaches a URL: a malformed token (e.g. an inner space)
    # makes http.client raise an error whose message contains the request path.
    if not TOKEN_PATTERN.fullmatch(token):
        sys.exit(f"error: {TOKEN_KEY} does not look like a bot token (expected <digits>:<letters>).")
    if not CHAT_ID_PATTERN.fullmatch(chat_id):
        sys.exit(f"error: {CHAT_KEY} must be a numeric chat id or an @channel name.")
    return token, chat_id


def send_message(token: str, chat_id: str, text: str, parse_mode: str | None) -> None:
    """POST to the Telegram sendMessage API; exit with an error line on failure."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(detail)
            if isinstance(parsed, dict):
                detail = parsed.get("description", detail)
        except ValueError:
            pass
        sys.exit(f"error: Telegram API returned HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"error: could not reach Telegram: {exc.reason}")
    except (TimeoutError, OSError, ValueError) as exc:
        # Report only the exception type: some messages can include the request URL.
        sys.exit(f"error: request to Telegram failed ({type(exc).__name__})")
    if not isinstance(body, dict) or not body.get("ok"):
        description = body.get("description") if isinstance(body, dict) else body
        sys.exit(f"error: Telegram rejected the message: {description}")


def force_utf8_output() -> None:
    """Print UTF-8 regardless of the console codepage (Windows consoles may be cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main() -> None:
    force_utf8_output()
    parser = argparse.ArgumentParser(description="Send a Telegram message via your notify bot.")
    parser.add_argument("message", help="message text, or '-' to read from stdin")
    parser.add_argument("--html", action="store_true", help="parse the text as Telegram HTML")
    args = parser.parse_args()

    text = (sys.stdin.read() if args.message == "-" else args.message).strip()
    if not text:
        sys.exit("error: empty message")
    if len(text) > MAX_MESSAGE_CHARS:
        sys.exit(f"error: message is {len(text)} chars; Telegram allows {MAX_MESSAGE_CHARS}")

    token, chat_id = load_credentials()
    send_message(token, chat_id, text, "HTML" if args.html else None)
    print("ok: message sent")


if __name__ == "__main__":
    main()
