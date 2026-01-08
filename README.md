# Facebook Marketplace iPhone Flipper Bot

Docker-based bot that monitors Facebook Marketplace for newly listed iPhones
and sends Telegram alerts optimized for phone flipping.

## Features
- Profit estimation + grading
- Just-listed alerts
- Heartbeat monitoring
- CSV logging
- CasaOS / Docker compatible

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/fb-marketplace-iphone-flipper.git
cd fb-marketplace-iphone-flipper
cp .env.example .env
docker compose up -d
