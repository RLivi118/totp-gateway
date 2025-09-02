"""
Zulip TOTP Bot (sanitized demo)
- DM commands:
    1) !mfa-<client>-<service>
    2) code <label>
- Replies with current 6-digit TOTP fetched from the gateway.
- Optional audit: posts an event to a stream (topic "channel events" by default).
- All secrets must come from environment variables (.env) — never commit real values.

Required env (see bot/.env.example):
  ZULIP_ORG_URL="https://your-org.zulipchat.com"
  ZULIP_BOT_EMAIL="totp-bot@your-org.zulipchat.com"
  ZULIP_BOT_TOKEN="replace_me"
  GATEWAY_URL="http://localhost:8000"  # demo
  ALLOWED_SENDERS="alice@example.com,bob@example.com"  # optional, blank = allow all (demo)
  AUDIT_STREAM="general"               # optional; if set, will post audit events
  AUDIT_TOPIC="channel events"         # optional; default below

This demo talks to the portfolio gateway endpoint:
  GET {GATEWAY_URL}/code?label=<label>
"""

import os
import re
import time
import json
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

ORG = os.getenv("ZULIP_ORG_URL", "").rstrip("/")
BOT_EMAIL = os.getenv("ZULIP_BOT_EMAIL", "")
BOT_TOKEN = os.getenv("ZULIP_BOT_TOKEN", "")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000").rstrip("/")
ALLOWED_SENDERS = {
    s.strip().lower() for s in os.getenv("ALLOWED_SENDERS", "").split(",") if s.strip()
}
AUDIT_STREAM = os.getenv("AUDIT_STREAM", "").strip()
AUDIT_TOPIC = os.getenv("AUDIT_TOPIC", "channel events").strip() or "channel events"

if not (ORG and BOT_EMAIL and BOT_TOKEN):
    raise SystemExit("Missing required env: ZULIP_ORG_URL, ZULIP_BOT_EMAIL, ZULIP_BOT_TOKEN")

API = f"{ORG}/api/v1"
session = requests.Session()
session.auth = (BOT_EMAIL, BOT_TOKEN)
session.headers.update({"User-Agent": "lsr-totp-bot/1.0"})

CMD_MFA = re.compile(r"^!mfa-([a-z0-9_\-]+)-([a-z0-9_\-]+)$", re.IGNORECASE)
CMD_CODE = re.compile(r"^code\s+([^\s]+)$", re.IGNORECASE)  # label may include dashes/underscores

def _send_dm(user_id: int, content: str) -> None:
    r = session.post(f"{API}/messages", data={"type": "private", "to": [user_id], "content": content}, timeout=10)
    r.raise_for_status()

def _send_stream(stream: str, topic: str, content: str) -> None:
    if not stream:
        return
    payload = {"type": "stream", "to": stream, "topic": topic, "content": content}
    r = session.post(f"{API}/messages", data=payload, timeout=10)
    r.raise_for_status()

def _register_queue() -> dict:
    r = session.post(f"{API}/register", data={"event_types": json.dumps(["messages"])}, timeout=15)
    r.raise_for_status()
    return r.json()

def _get_events(queue_id: str, last_event_id: int) -> dict:
    r = session.get(
        f"{API}/events",
        params={"queue_id": queue_id, "last_event_id": last_event_id, "dont_block": False, "timeout": 90},
        timeout=95,
    )
    r.raise_for_status()
    return r.json()

def _fetch_code_for_label(label: str) -> str:
    # Gateway demo endpoint: /code?label=...
    r = requests.get(f"{GATEWAY_URL}/code", params={"label": label}, timeout=6)
    if r.status_code == 404:
        return "Unknown label."
    r.raise_for_status()
    data = r.json()
    return data.get("code", "error")

def _allowed(sender_email: str) -> bool:
    return (not ALLOWED_SENDERS) or (sender_email.lower() in ALLOWED_SENDERS)

def _handle_text(text: str) -> Optional[str]:
    """
    Returns the label to use with the gateway, or None if the text isn't a command.
    - '!mfa-client-service'  -> label 'client-service'
    - 'code label'           -> label 'label'
    """
    m1 = CMD_MFA.match(text)
    if m1:
        client, service = m1.group(1), m1.group(2)
        return f"{client}-{service}"

    m2 = CMD_CODE.match(text)
    if m2:
        return m2.group(1)

    if text.strip().lower() in {"!mfa-help", "help"}:
        return ""  # special marker to print help

    return None

HELP_TEXT = (
    "**TOTP bot (demo):**\n"
    "• `!mfa-<client>-<service>` → replies with current 6-digit code for that label\n"
    "• `code <label>` → same as above (demo-friendly)\n"
    "_Notes:_ Allowed senders only (if configured). All secrets live in env/secret manager."
)

def main() -> None:
    print("Registering Zulip event queue…")
    q = _register_queue()
    queue_id = q["queue_id"]
    last_event_id = q["last_event_id"]
    print("Listening for DMs…")

    while True:
        try:
            ev = _get_events(queue_id, last_event_id)
            for e in ev.get("events", []):
                last_event_id = e["id"]
                if e.get("type") != "message":
                    continue

                msg = e.get("message", {})
                if msg.get("type") != "private":  # DM only
                    continue

                sender_email = (msg.get("sender_email") or "").lower()
                if not _allowed(sender_email):
                    continue  # silently ignore disallowed senders in demo

                text = (msg.get("content") or "").strip()
                label = _handle_text(text)

                if label is None:  # not a command
                    continue

                if label == "":   # help
                    _send_dm(msg["sender_id"], HELP_TEXT)
                    continue

                # Fetch code
                code = _fetch_code_for_label(label)
                _send_dm(msg["sender_id"], f"`{label}` → **{code}**")

                # Optional audit
                if AUDIT_STREAM:
                    _send_stream(
                        AUDIT_STREAM,
                        AUDIT_TOPIC,
                        f"requester: `{sender_email}` • label: `{label}` • replied in DM",
                    )

        except requests.HTTPError as he:
            print("HTTP error:", he)
            time.sleep(2)
        except Exception as ex:
            print("Error:", ex)
            time.sleep(2)

if __name__ == "__main__":
    main()
