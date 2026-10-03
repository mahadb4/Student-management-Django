#!/usr/bin/env bash
set -euo pipefail

IMAGE_TAG="${1:?usage: deploy.sh <image-tag>}"

REGION="us-east-1"
REGISTRY="329871097711.dkr.ecr.${REGION}.amazonaws.com"
REPOSITORY="student-management-backend"
APP_DIR="/home/ec2-user/student-management"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$APP_DIR"

[ -f .env ] || { echo "ERROR: $APP_DIR/.env not found"; exit 1; }
[ -f "$COMPOSE_FILE" ] || { echo "ERROR: $COMPOSE_FILE not found"; exit 1; }
docker compose version >/dev/null || { echo "ERROR: docker compose is not available"; exit 1; }

export BACKEND_IMAGE="${REGISTRY}/${REPOSITORY}:${IMAGE_TAG}"
compose() { docker compose --env-file .env -f "$COMPOSE_FILE" "$@"; }

echo "Deploying $BACKEND_IMAGE"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

compose pull web
compose up -d

if grep -q '^BACKEND_IMAGE=' .env; then
  sed -i "s|^BACKEND_IMAGE=.*|BACKEND_IMAGE=${BACKEND_IMAGE}|" .env
else
  printf '\nBACKEND_IMAGE=%s\n' "$BACKEND_IMAGE" >> .env
fi

compose run --rm --no-deps -T web python manage.py migrate --noinput

HEALTH_HOST="$(grep '^ALLOWED_HOSTS=' .env | tail -n1 | cut -d= -f2- | cut -d, -f1 | tr -d "\"' \r")"
HEALTH_HOST="${HEALTH_HOST:-127.0.0.1}"

for attempt in $(seq 1 30); do
  if curl -fsS -o /dev/null -H "Host: ${HEALTH_HOST}" http://127.0.0.1:8000/admin/login/; then
    echo "Health check passed"
    docker image prune -af --filter "until=72h" >/dev/null || true
    exit 0
  fi
  sleep 2
done

echo "ERROR: health check failed after deploy"
compose ps
compose logs --tail=50 web
exit 1
