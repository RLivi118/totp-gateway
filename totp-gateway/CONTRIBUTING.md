# Contributing

This repository is presented as a **sanitized portfolio project**. If you fork it:
- Do not commit real tokens, seeds, org URLs, or stream names.
- Keep `.env` files local and untracked (see `.gitignore`).

## Sanitization Checklist (pre‑publish)

- [ ] Replace all real org/stream names with neutral placeholders.
- [ ] Keep only fake demo seeds in `gateway/.env.example`.
- [ ] Ensure `ZULIP_BOT_TOKEN` is never committed; keep it as `replace_me` in `.env.example`.
- [ ] Remove real logs; include synthetic samples only.
- [ ] Document network restrictions (VPN/allowlist) in README.
