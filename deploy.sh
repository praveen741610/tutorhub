#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.prod.yml}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed. Install Docker first."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "docker compose is not available. Install Docker Compose plugin."
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT_DIR/.env.prod.example" "$ENV_FILE"
  echo "Created $ENV_FILE from template."
  echo "Edit it first (DOMAIN, LETSENCRYPT_EMAIL, passwords, JWT_SECRET), then rerun."
  exit 1
fi

required_vars=("DOMAIN" "LETSENCRYPT_EMAIL" "POSTGRES_PASSWORD" "JWT_SECRET")
for key in "${required_vars[@]}"; do
  if ! grep -Eq "^${key}=.+" "$ENV_FILE"; then
    echo "Missing required value: $key in $ENV_FILE"
    exit 1
  fi
done

echo "Using env file: $ENV_FILE"
"${COMPOSE_CMD[@]}" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull
"${COMPOSE_CMD[@]}" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build
"${COMPOSE_CMD[@]}" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo ""
echo "Deployment complete."
echo "Check logs: ${COMPOSE_CMD[*]} --env-file $ENV_FILE -f $COMPOSE_FILE logs -f"
