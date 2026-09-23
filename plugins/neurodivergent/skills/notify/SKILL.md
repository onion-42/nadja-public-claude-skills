---
name: notify
description: >-
  Send the user a short Telegram message through THEIR OWN notify bot (a stdlib Python script →
  Telegram sendMessage API; token read from environment variables, never printed). Use in three
  cases. (1) They ask: "notify me", "ping me", "let me know when it's done", "/notify". (2) A LONG
  or BACKGROUND task just finished (build, training run, batch job, anything they started and
  walked away from) — one "done" line so they don't have to watch the screen. (3) Claude is
  BLOCKED waiting for their answer or decision mid-task — one short line so the question isn't
  missed. Do NOT ping for quick tasks or on every message.
user-invocable: true
---

# notify — "done" and "waiting for you"

Out of sight is out of mind: a finished job or a pending question in a terminal nobody is looking
at can sit for hours. This skill sends one short message to the user's phone.

## When to use (three cases)

1. **Explicit request** — "notify me", "ping me", "let me know when it's done", `/notify`.
2. **Long / background task finished** — send one line: what finished + the key result.
3. **Blocked waiting on the user** — Claude stopped mid-task and needs a decision. Send one line
   naming the question.

**Do NOT** ping for tasks that finish while the user is watching, and never send more than one
ping for the same event. A notification nobody needed is noise.

## How to send

The script sits next to this SKILL.md, in this skill's base directory:

```bash
python "<this skill's dir>/send_telegram.py" "✅ Tests done: 212 passed, 0 failed."
```

- `--html` — parse as Telegram HTML (`<b>`, `<i>`, `<code>`).
- message `-` — read the body from stdin (for multi-line text).

Success prints `ok: message sent`. A failure prints one `error:` line and exits non-zero — tell the
user what it says; don't retry silently.

## Message style

- One line when possible. Lead with a status glyph: ✅ done · ⚠️ needs input · ❌ failed ·
  ⏳ still running.
- Include the concrete result or the exact question — not just "done".
- Never put secrets, tokens, personal data or long logs in a message.

## One-time setup (bring your own bot)

1. In Telegram, talk to **@BotFather** → `/newbot` → copy the bot token.
2. Send any message to your new bot, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy `chat.id`.
3. Set two environment variables for the shell Claude Code runs in:
   `NOTIFY_TELEGRAM_TOKEN` and `NOTIFY_TELEGRAM_CHAT_ID` (for example in `~/.bashrc`, or in
   Windows user environment variables). Restart Claude Code.

The token is only read into memory — the script never prints or logs it. Claude must never echo
these variables either. Check with your organisation before routing work notifications through
Telegram; do not send confidential content.
