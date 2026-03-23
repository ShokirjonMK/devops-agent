#!/bin/sh
set -e
export DATABASE_URL="${DATABASE_URL:-postgresql://devops:devops@postgres:5432/devops_agent}"
cd /app
alembic upgrade head
exec "$@"
