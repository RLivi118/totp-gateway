#!/usr/bin/env python3
"""
LSR TOTP Bot (production-like, sanitized)

Features:
- Commands:
    • !mfa-<client>-<service>    (DM or mention in stream)
    • !mfa-help / !mfa
- Channel access control: requester must be a member of #<client>
- Audit logging: posts to client stream under topic "channel events", fallback to #general
- Gateway call: GET {GATEWAY_URL}/totp/<client>/<service>
  Optionally sends Authorization: Bearer <API_KEY> if API_KEY is set.
- Secrets/config from zuliprc + environment variables.

Env (all optional but recommended):
  GATEWAY_URL="http://localhost:8000"   # demo default
  API_KEY=""                             # if set, add Authorization: Bearer <API_KEY>
  AUDIT_TOPIC="channel events"
  FALLBACK_STREAM="general"
  ZULIPRC_PATH="./zuliprc"               # path to zuliprc (default: ./zuliprc)

Safety:
- No real client names, URLs, or tokens appear in this repository.
- Never commit a real zuliprc; only commit zuliprc.example.
"""

import os
import re
import time
import logging
from typing import List, Dict, Optional

import requests
import zulip  # official zulip client

# ---------- Config ----------
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("API_KEY", "").strip()  # optional; when set we add Bearer token
AUDIT_TOPIC = os.getenv("AUDIT_TOPIC", "channel events").strip() or "channel events"
FALLBACK_STREAM = os.getenv("FALLBACK_STREAM", "general").strip() or "general"
ZULIPRC_PATH = os.getenv("ZULIPRC_PATH", "./zuliprc")

# Demo: sanitized mapping for display names (safe placeholders only)
SERVICE_DISPLAY = {
    "gmail": "Gmail",
    "aws": "AWS",
    "slack": "Slack",
    "microsoft": "Microsoft",
    "github": "GitHub",
    "demo": "Demo",
}

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lsr-totp-bot")

# ---------- Command patterns ----------
CMD_HELP = re.compile(r"(^|\s)!mfa(\s|$)|(^|\s)!mfa-help(\s|$)", re.IGNORECASE)
CMD_MFA = re.compile(r"!mfa-(?!help\b)([a-z0-9_]+)-([a-z0-9_]+)\b", re.IGNORECASE)

# ---------- Helpers ----------
def create_client() -> zulip.Client:
    # use zuliprc exactly like production; never commit a real one
    return zulip.Client(config_file=ZULIPRC_PATH)

def get_self_identity(client: zulip.Client):
    prof = client.get_profile()
    if prof.get("result") == "success":
        return prof.get("email"), prof.get("user_id")
    return None, None

def list_streams(client: zulip.Client) -> Dict[str, dict]:
    res = client.get_streams()
    if res.get("result") != "success":
        raise RuntimeError(f"get_streams failed: {res}")
    # name(lower) -> metadata
    return {s["name"].lower(): s for s in res.get("streams", [])}

def get_user_id_and_name(client: zulip.Client, email: str) -> (Optional[int], str):
    res = client.get_users()
    if res.get("result") == "success":
        for m in res.get("members", []):
            if m.get("email") == email:
                return m.get("user_id"), m.get("full_name") or email.split("@")[0]
    # fallback
    return None, email.split("@")[0]

def user_stream_memberships(client: zulip.Client, user_id: int, stream_map: Dict[str, dict]) -> List[str]:
    """Return list of stream names (lowercase) that contain the user."""
    memberships = []
    for name, meta in stream_map.items():
        res = client.get_subscribers(stream=name)
        if res.get("result") == "success":
            if user_id in res.get("subscribers", []):
                memberships.append(name)
    return memberships

def in_client_stream(client: zulip.Client, client_name: str, user_id: int, stream_map: Dict[str, dict]) -> bool:
    """Require membership in #<client_name>."""
    subs = client.get_subscribers(stream=client_name)
    if subs.get("result") != "success":
        return False
    return user_id in subs.get("subscribers", [])

def send_dm(client: zulip.Client, to_email: str, content: str):
    client.send_message({"type": "private", "to": [to_email], "content": content})

def send_stream_message(client: zulip.Client, stream_name: str, topic: str, content: str) -> bool:
    stream_map = list_streams(client)
    meta = stream_map.get(stream_name.lower())
    if not meta:
        log.error("No such stream #%s", stream_name)
        return False
    payload = {"type": "stream", "to": meta["stream_id"], "topic": topic, "content": content}
    res = client.send_message(payload)
    return res.get("result") == "success"

def fetch_totp(label_client: str, label_service: str, requester_email: str) -> (bool, str, Optional[dict]):
    """Call portfolio gateway route /totp/<client>/<service>"""
    url = f"{GATEWAY_URL}/totp/{label_client}/{label_service}"
    headers = {"X-Zulip-User": requester_email}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 404:
            return False, "Unknown label.", None
        r.raise_for_status()
        data = r.json()
        return True, "", data
    except Exception as e:
        return False, f"Gateway error: {e}", None

HELP_TEXT = (
    "🔐 **TOTP Bot — Usage**\n\n"
    "**Commands**\n"
    "• `!mfa-<client>-<service>` — DM me or mention me in the right stream\n"
    "• `!mfa-help` — show this help\n\n"
    "**Access control**\n"
    "• You must be a member of `#<client>` to request codes for that client.\n\n"
    "**Audit**\n"
    f"• Logs to the client’s stream under topic **“{AUDIT_TOPIC}”**, fallback to `#{FALLBACK_STREAM}`.\n"
)

def main():
    client = create_client()
    me_email, me_id = get_self_identity(client)
    log.info("Bot started. me_email=%s me_id=%s gateway=%s", me_email, me_id, GATEWAY_URL)

    def handler(event):
        if event.get("type") != "message":
            return

        msg = event.get("message", {})
        text = (msg.get("content") or "").strip()
        msg_type = msg.get("type")
        sender_email = msg.get("sender_email", "")
        sender_id = msg.get("sender_id")

        # Ignore ourselves / other bots
        if (me_id is not None and sender_id == me_id) or msg.get("sender_is_bot"):
            return

        # Only respond to DMs or mentions
        if msg_type != "private" and "@**" not in text:
            return

        # Help
        if CMD_HELP.search(text):
            send_dm(client, sender_email, HELP_TEXT)
            return

        # Parse !mfa-client-service
        m = CMD_MFA.search(text.lower())
        if not m:
            return
        label_client, label_service = m.group(1), m.group(2)

        # Access control: must be in #<client>
        stream_map = list_streams(client)
        user_id, display_name = get_user_id_and_name(client, sender_email)
        if user_id is None or not in_client_stream(client, label_client, user_id, stream_map):
            send_dm(
                client,
                sender_email,
                f"❌ **Access Denied**\n\n"
                f"You must be in **#{label_client}** to request `{label_service}` codes.\n"
                f"Please contact an admin for access."
            )
            # Log denial (try client stream, then fallback)
            denied = f"❌ {display_name} requested {SERVICE_DISPLAY.get(label_service, label_service)} MFA → Access denied (not in #{label_client})"
            if not send_stream_message(client, label_client, AUDIT_TOPIC, denied):
                send_stream_message(client, FALLBACK_STREAM, AUDIT_TOPIC, f"{denied} (logged here)")
            return

        # Fetch code from gateway
        ok, err, data = fetch_totp(label_client, label_service, sender_email)
        if not ok:
            send_dm(client, sender_email, f"❌ {err}")
            msg_txt = f"⚠️ {display_name} requested {SERVICE_DISPLAY.get(label_service, label_service)} MFA → ❌ {err}"
            if not send_stream_message(client, label_client, AUDIT_TOPIC, msg_txt):
                send_stream_message(client, FALLBACK_STREAM, AUDIT_TOPIC, f"{msg_txt} (logged here)")
            return

        # Reply in DM
        code = data.get("code", "error")
        valid_for = data.get("valid_for", 30)
        ts = (data.get("timestamp") or "")[:19]
        dm_text = (
            f"🔐 **{SERVICE_DISPLAY.get(label_service, label_service)}** "
            f"({label_client}): `{code}`\n"
            f"⏰ Valid for {valid_for} seconds\n"
            f"🕒 Generated at {ts}"
        )
        send_dm(client, sender_email, dm_text)

        # Audit success
        log_txt = f"🔐 {display_name} requested {SERVICE_DISPLAY.get(label_service, label_service)} MFA → ✅ Code sent to DM"
        if not send_stream_message(client, label_client, AUDIT_TOPIC, log_txt):
            send_stream_message(client, FALLBACK_STREAM, AUDIT_TOPIC, f"{log_txt} (logged here)")

    client.call_on_each_message(handler)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            log.error("Fatal error: %s", e)
            time.sleep(2)
