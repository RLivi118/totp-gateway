# Systemd Units

Install (example):
```bash
sudo mkdir -p /opt/lsr/totp-gateway
sudo cp -r bot gateway /opt/lsr/totp-gateway/
sudo cp infra/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gateway bot
sudo systemctl start gateway bot
```
