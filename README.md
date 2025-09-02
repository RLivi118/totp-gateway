# Zulip TOTP Bot - Secure MFA Code Gateway

*Secure team access to TOTP codes via Zulip chat integration*

A production-ready setup that exposes a **TOTP code gateway** (FastAPI) and a **Zulip bot** that returns 6-digit MFA codes on request. All secrets are pulled from environment variables or config files — never committed to GitHub.

> **Note:** This repository is sanitized for public viewing. All seeds, tokens, org names, and streams in examples are **fake**.

---

## Problem → Solution

- **Problem:** Teams sometimes need a short-lived one-time code to complete a login step, but the seed is locked in a secure vault or gateway that isn't convenient to reach from chat.  
- **Solution:** A minimal **gateway** that holds secured secrets and a **Zulip bot** that returns a 6-digit TOTP for an allowed label when asked.

---

## Architecture

```
User (Zulip DM)
      |
      |  "!mfa-<client>-<service>"
      v
Zulip Bot  --(HTTP request)-->  FastAPI Gateway  --(read)-->  TOTP Seeds
      |                               |
      |<------- 6-digit TOTP ---------|
      v
Reply in DM: 123456
```

- **Gateway**: `/code?label=client-demo` and `/totp/<client>/<service>` → returns JSON with a 6-digit code.  
- **Bot**: listens to DMs (or mentions), checks access, hits the gateway, and replies.

---

## Prerequisites

- Python 3.8+
- Zulip server access with bot permissions
- Basic familiarity with TOTP/2FA concepts
- Network access between bot and gateway components

---

## Quick Start (Demo)

> This repo never contains real tokens or seeds. Copy `.env.example` → `.env` locally with **fake** values.

### Gateway
```bash
cd gateway
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # contains fake demo seed
uvicorn app:app --reload
```

### Bot
```bash
cd bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # placeholders only, keep token private
python main.py
```

---

## Gateway Endpoints

This project exposes **two routes** for flexibility:

- **Demo-friendly route**  
  `GET /code?label=client-demo`  
  → Quick and easy way to test locally with a single label.

- **Realistic route**  
  `GET /totp/<client>/<service>`  
  → Mirrors a production API shape (with optional Bearer token).  
  Example: `/totp/client/demo` →  
  ```json
  {"client":"client","service":"demo","code":"123456","valid_for":30,"timestamp":"2025-09-02T22:30:00Z"}
  ```

Both routes return current 6-digit TOTPs based on the fake demo seed in `.env.example`.

---

## Demo Commands

- In Zulip DM:  
  `!mfa-client-demo` → bot replies with a 6-digit code.  
- Or HTTP test:  
  `GET /code?label=client-demo` → `{ "code": "123456", "period": 30 }`

---

## Security Best Practices

- **Never commit secrets**: All TOTP seeds stored in environment variables
- **Network isolation**: Gateway should run behind VPN/firewall  
- **Access control**: Bot validates user permissions before responding
- **Audit logging**: All code requests are logged with timestamps
- **Token rotation**: Implement regular TOTP seed rotation in production
- **Time synchronization**: Ensure system clocks are synchronized between components
- **Rate limiting**: Implement request throttling to prevent abuse

### Production Security Notes

- This repo uses **fake demo seeds** only.  
- In production, use KMS/Key Vault/Secrets Manager, seed rotation, and strict allowlisting.  
- Gateway should only be reachable via VPN or IP allowlist.  
- Bot and gateway read **all secrets from env or config files**, never from source code.  

---

## Troubleshooting

**Bot not responding:**
- Check Zulip bot permissions and network connectivity
- Verify `.env` file exists and contains valid credentials
- Check bot logs for authentication errors

**Invalid or expired codes:**
- Verify system time synchronization between gateway and client
- Ensure TOTP seeds are correctly configured
- Check if codes are being generated too quickly (30-second window)

**HTTP 403/500 errors:**
- Confirm environment variables are properly set
- Verify gateway is running and accessible
- Check network connectivity between bot and gateway

**Gateway connection issues:**
- Ensure FastAPI server is running on correct port
- Verify firewall rules allow communication
- Check logs for detailed error messages

---

## Roadmap

- Integrate KMS/Key Vault with envelope encryption  
- Add rotation policy and audit export (e.g., to CloudWatch/ELK)  
- High availability (multi-instance + health checks)  
- Structured metrics and rate limiting  
- Web dashboard for code management
- Multi-tenant support with role-based access

---

## Repository Structure

```
.
├── bot/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example
│   └── zuliprc.example
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

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Portfolio tags:** `python`, `fastapi`, `zulip-bot`, `totp`, `2fa`, `mfa`, `security`, `infrastructure`, `portfolio-project`
