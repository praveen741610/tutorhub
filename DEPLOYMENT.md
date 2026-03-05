# Production Deployment (24/7)

This setup keeps the website online continuously using:
- `postgres` database
- `api` service (FastAPI + Alembic migrations)
- `caddy` reverse proxy with automatic HTTPS (Let's Encrypt)

All services use `restart: unless-stopped` for auto-restart after host reboot/crash.

## 1) Server prerequisites

- Ubuntu 22.04+ VPS (or similar Linux server)
- Domain name pointed to server IP (`A` record)
- Open firewall ports: `80` and `443`

Install Docker:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

## 2) Copy project

```bash
git clone <your-repo-url> tutorhub
cd tutorhub
```

## 3) Configure environment

```bash
cp .env.prod.example .env.prod
```

Edit `.env.prod` and set real values:
- `DOMAIN` (example: `academy.yourdomain.com`)
- `LETSENCRYPT_EMAIL`
- strong `POSTGRES_PASSWORD`
- strong `JWT_SECRET`

## 4) Deploy

```bash
chmod +x deploy.sh
./deploy.sh
```

## 5) Verify

- `https://YOUR_DOMAIN/`
- `https://YOUR_DOMAIN/api`
- `https://YOUR_DOMAIN/docs`

## Operations

Restart stack:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml restart
```

View logs:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f
```

Upgrade after code changes:

```bash
git pull
./deploy.sh
```
