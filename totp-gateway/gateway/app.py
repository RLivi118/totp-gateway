from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import os
import pyotp

app = FastAPI(title="TOTP Gateway (Demo)")

def load_label_map():
    # LABELS is like: "certus:JBSWY3DPEHPK3PXP,alpha:GEZDGNBVGY3TQOJQ"
    raw = os.getenv("LABELS", "")
    mapping = {}
    for pair in [p.strip() for p in raw.split(",") if p.strip()]:
        if ":" in pair:
            label, seed = pair.split(":", 1)
            mapping[label.strip()] = seed.strip()
    return mapping

def totp_for(seed: str, period: int = 30, digits: int = 6) -> str:
    totp = pyotp.TOTP(seed, interval=period, digits=digits)
    return totp.now()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/code")
def code(label: str = Query(..., min_length=1)):
    labels = load_label_map()
    if label not in labels:
        raise HTTPException(status_code=404, detail="unknown label")
    period = int(os.getenv("TOTP_PERIOD", "30"))
    digits = int(os.getenv("TOTP_DIGITS", "6"))
    seed = labels[label]
    return JSONResponse({"code": totp_for(seed, period, digits), "period": period})
