# TOTP Gateway + Zulip Bot (Portfolio Project)

A small, demo-friendly setup that exposes a **TOTP code gateway** (FastAPI) and a **Zulip bot** that returns 6-digit codes on request. All secrets are pulled from environment variables or config files — never committed to GitHub.

> **Note:** This repository is sanitized for public viewing. All seeds, tokens, org names, and streams in examples are **fake**.

---

## Problem → Solution

- **Problem:** Teams sometimes need a short-lived one-time code to complete a login step, but the seed is locked in a secure vault or gateway that isn’t convenient to reach from chat.  
- **Solution:** A minimal **gateway** that holds fake demo seeds (or, in real life, secured secrets) and a **Zulip bot** that returns a 6-digit TOTP for an allowed label when asked.

---

## Architecture

```mermaid
flowchart LR
  U[User (Zulip DM)] -- "!mfa-client-service" --> B[Zulip Bot]
  B -->|HTTP request| G[FastAPI Gateway]
  subgraph Secrets
    S[TOTP Seeds (env/KMS/Vault)]
  end
  G --> S
  G -->|6-digit TOTP| B
  B -->|reply 123456| U
