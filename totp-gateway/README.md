# TOTP Gateway + Zulip Bot (Portfolio Project)

A small, demo-friendly setup that exposes a **TOTP code gateway** (FastAPI) and a **Zulip bot** that returns 6‑digit codes on request—wired to environment variables so you never commit secrets.

> **Note:** This repository is sanitized for public viewing. All seeds, tokens, org names, and streams in examples are **fake**.

## Problem → Solution

- **Problem:** Team members sometimes need a short-lived one-time code to complete a login step, but the code is locked in a secure vault or service that isn't convenient to reach from chat.
- **Solution:** A minimal **gateway** that holds *fake* demo seeds (or, in real life, secured secrets) and a **Zulip bot** that returns a 6‑digit TOTP for an allowed label when asked in a DM.

## Architecture

```mermaid
flowchart LR
  U[User (Zulip DM)] -- "code <label>" --> B[Zulip Bot]
  B -->|HTTP request| G[FastAPI Gateway]
  subgraph Secrets
    S[TOTP Seeds (env/KMS/Vault)]
  end
  G --> S
  G -->|6-digit TOTP| B
  B -->|reply 123456| U
```

- Gateway: FastAPI app (`/code?label=...`) looks up the seed by `label`, calculates TOTP, returns code.
- Bot: Listens to Zulip DMs; if sender is allowed and channel is permitted, asks gateway for the code and replies.

## Quick Start (Demo)

> Create two virtual environments (one for each component) or run them separately.
>
> **Never put real tokens/seeds in this repo.** Use environment variables or secret managers.

### Gateway

```bash
cd gateway
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# copy .env.example to .env and edit with FAKE seeds only
uvicorn app:app --reload
```

### Bot

```bash
cd bot
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# copy .env.example to .env and edit placeholders (keep token private)
python main.py
```

## Demo Commands

- In Zulip DM, send: `code certus` → bot replies with a 6‑digit code.
- HTTP test: `GET /code?label=certus` → `{ "code": "123456", "period": 30 }`

## Security Notes

- This public repo uses **fake demo seeds**. In real deployments, use KMS/Key Vault, rotation, and allowlisting.
- The gateway should be reachable only over VPN or IP allowlist.
- Bot and gateway read **all sensitive values** from environment variables.

## What I’d Improve Next

- KMS/Key Vault integration with envelope encryption
- Rotation policy and audit export (e.g., to CloudWatch/ELK)
- High availability (multi-instance + health checks)
- Structured metrics and rate limiting

## Repository Map

```
.
├── bot/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── gateway/
│   ├── app.py
│   ├── requirements.txt
│   └── .env.example
├── infra/
│   ├── docker-compose.yml
│   └── systemd/
│       ├── gateway.service
│       ├── bot.service
│       └── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── .gitignore
└── README.md
```

---

*Portfolio tags:* `python`, `fastapi`, `zulip-bot`, `totp`, `2fa`, `mfa`, `security`, `infrastructure`
