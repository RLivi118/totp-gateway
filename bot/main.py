import os
import re
import time
import json
import requests
from dotenv import load_dotenv

# You can also use official Zulip bot framework; this minimal loop uses Zulip's REST endpoints.
# For portfolio/demo purposes only.

load_dotenv()

ORG = os.getenv("ZULIP_ORG_URL", "").rstrip("/")
BOT_EMAIL = os.getenv("ZULIP_BOT_EMAIL", "")
BOT_TOKEN = os.getenv("ZULIP_BOT_TOKEN", "")
ALLOWED_SENDERS = {s.strip().lower() for s in os.getenv("ALLOWED_SENDERS", "").split(",") if s.strip()}
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000").rstrip("/")

if not (ORG and BOT_EMAIL and BOT_TOKEN):
    raise SystemExit("Missing required env: ZULIP_ORG_URL, ZULIP_BOT_EMAIL, ZULIP_BOT_TOKEN")

API = f"{ORG}/api/v1"
session = requests.Session()
session.auth = (BOT_EMAIL, BOT_TOKEN)

def send_dm(user_id: int, content: str):
    payload = {"type": "private", "to": [user_id], "content": content}
    r = session.post(f"{API}/messages", data=payload, timeout=10)
    r.raise_for_status()

def get_events(queue_id, last_event_id):
    r = session.get(f"{API}/events", params={"queue_id": queue_id, "last_event_id": last_event_id, "dont_block": False, "timeout": 90}, timeout=95)
    r.raise_for_status()
    return r.json()

def register_event_queue():
    r = session.post(f"{API}/register", data={"event_types": json.dumps(["messages"])}, timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_code(label: str) -> str:
    r = requests.get(f"{GATEWAY_URL}/code", params={"label": label}, timeout=5)
    if r.status_code == 404:
        return "Unknown label."
    r.raise_for_status()
    data = r.json()
    return data.get("code", "error")

def main():
    print("Registering Zulip event queue...")
    q = register_event_queue()
    queue_id = q["queue_id"]
    last_event_id = q["last_event_id"]
    print("Listening for DMs...")

    while True:
        try:
            ev = get_events(queue_id, last_event_id)
            for e in ev.get("events", []):
                last_event_id = e["id"]
                if e["type"] != "message":
                    continue
                msg = e["message"]
                if msg.get("type") != "private":
                    continue  # only DM
                sender = (msg.get("sender_email") or "").lower()
                if ALLOWED_SENDERS and sender not in ALLOWED_SENDERS:
                    continue
                text = (msg.get("content") or "").strip()
                m = re.match(r"^code\s+(\S+)$", text, flags=re.I)
                if m:
                    label = m.group(1)
                    code = fetch_code(label)
                    send_dm(msg["sender_id"], f"`{label}` → **{code}**")
        except requests.HTTPError as he:
            print("HTTP error:", he)
            time.sleep(2)
        except Exception as ex:
            print("Error:", ex)
            time.sleep(2)

if __name__ == "__main__":
    main()
