# totp-gateway
This project implements a secure TOTP gateway for distributed teams, integrated with a Zulip chat bot for on-demand MFA code delivery. Team members can request codes through Zulip, and access is automatically restricted by channel membership, ensuring that only authorized users can retrieve credentials.

The gateway runs behind a VPN and stores TOTP secrets in an encrypted environment, never exposing raw seeds in chat or logs. The system is designed for small, remote teams who need a cost-effective, reliable way to share MFA access without relying on insecure SMS or commercial apps.

By combining Python automation, secure networking, and chat-ops integration, this project demonstrates practical infrastructure security and workflow automation that can scale with growing teams.
