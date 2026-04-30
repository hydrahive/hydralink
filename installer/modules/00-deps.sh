#!/usr/bin/env bash
# Native deps via apt: postgres, redis, python venv.
set -euo pipefail

apt-get update
apt-get install -y --no-install-recommends \
  postgresql postgresql-contrib \
  redis-server \
  python3 python3-venv python3-pip \
  build-essential libpq-dev \
  curl ca-certificates

# Redis: bind nur auf 127.0.0.1 (Default in Ubuntu — bestätigen).
# Wenn /etc/redis/redis.conf existiert und 'bind' nicht 127.0.0.1 sagt → fix.
if grep -qE '^bind 0\.0\.0\.0' /etc/redis/redis.conf 2>/dev/null; then
  sed -i 's/^bind 0\.0\.0\.0/bind 127.0.0.1/' /etc/redis/redis.conf
  systemctl restart redis-server
fi

systemctl enable --now postgresql redis-server
