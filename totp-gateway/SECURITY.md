# Security

This repository intentionally avoids placing secrets in the codebase. For any real deployment:
- Use a secret manager (AWS KMS/Secrets Manager, Azure Key Vault, HashiCorp Vault, etc.).
- Restrict gateway access by VPN or strict IP allowlists.
- Enable request logging, rate limiting, and audit export.
- Rotate TOTP seeds and bot tokens routinely.
