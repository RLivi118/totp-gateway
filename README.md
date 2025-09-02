# TOTP Gateway + Zulip Bot (Portfolio Project)

This project demonstrates a secure **TOTP MFA stack** with two parts:

- **Gateway** — a FastAPI service that generates one-time passcodes (OTPs) from seeds.
- **Bot** — a Zulip bot that listens for DM commands and replies with the current OTP.

All sensitive values are **pulled from environment variables** (never hardcoded or committed).  
This repo is sanitized with **fake/demo seeds** and placeholder tokens.

---

## Problem → Solution

- **Problem:** Teams sometimes need a one-time MFA code available in chat, but the code is tied up in a vault or gateway that’s not convenient to access.  
- **Solution:** A minimal gateway that holds demo TOTP seeds, and a Zulip bot that, when DM’d `code <label>`, fetches the code from the gateway and replies to the requester.

---

## Architecture

```mermaid
flowchart LR
  U[Zulip User] -- "code <label>" --> B[Zulip Bot]
  B -->|HTTP request| G[FastAPI Gateway]
  subgraph Secrets
    S[TOTP Seeds (env/KMS/Vault)]
  end
  G --> S
  G -->|6-digit TOTP| B
  B -->|reply 123456| U
