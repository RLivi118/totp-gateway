from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.responses import JSONResponse
import os
import pyotp
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="TOTP Gateway (Demo + Realistic Routes)")

def _load_label_map():
    """
    LABELS env example:
      LABELS="client-demo:JBSWY3DPEHPK3PXP,alpha-svc:GEZDGNBVGY3TQOJQ"
    Keys are the labels you’ll query:
      - /code?label=client-demo
      - /totp/client/demo  -> looks up label "client-demo"
    """
    raw = os.getenv("LABELS", "")
    mapping = {}
    for pair in [p.strip() for p in raw.split(",") if p.strip()]:
        if ":" in pair:
            label, seed = pair.split(":", 1)
            mapping[label.strip()] = seed.strip()
    return mapping

def _totp_now(seed: str, period: int = 30, digits: int = 6) -> str:
    return pyotp.TOTP(seed, interval=period, digits=digits).now()

def _params():
    return (
        int(os.getenv("TOTP_PERIOD", "30")),
        int(os.getenv("TOTP_DIGITS", "6")),
    )

def _require_api_key(auth_header: str | None):
    """
    If API_KEY is set, require Authorization: Bearer <API_KEY>.
    If API_KEY is empty/unset, auth is disabled (demo mode).
    """
    expected = os.getenv("API_KEY", "").strip()
    if not expected:
        return
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="invalid token")

@app.get("/health")
def health():
    return {"ok": True}

# ---- Demo route: /code?label=<label> ----
@app.get("/code")
def code(label: str = Query(..., min_length=1), authorization: str | None = Header(default=None)):
    _require_api_key(authorization)
    labels = _load_label_map()
    if label not in labels:
        raise HTTPException(status_code=404, detail="unknown label")
    period, digits = _params()
    return JSONResponse({"code": _totp_now(labels[label], period, digits), "period": period})

# ---- Realistic route: /totp/<client>/<service> ----
@app.get("/totp/{client}/{service}")
def totp(client: str, service: str, authorization: str | None = Header(default=None), x_zulip_user: str | None = Header(default=None)):
    """
    Portfolio-safe mirror of production:
      - Optional bearer auth via API_KEY
      - Returns code + valid_for + timestamp (UTC)
      - Keeps X-Zulip-User for realism (not used here)
    """
    _require_api_key(authorization)
    label = f"{client}-{service}"
    labels = _load_label_map()
    if label not in labels:
        raise HTTPException(status_code=404, detail="unknown label")
    period, digits = _params()
    code = _totp_now(labels[label], period, digits)
    now = datetime.now(timezone.utc).isoformat()
    return {"client": client, "service": service, "code": code, "valid_for": period, "timestamp": now}
