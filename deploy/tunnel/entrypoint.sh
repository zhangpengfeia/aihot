#!/bin/sh
set -eu
: "${SSH_HOST:?set SSH_HOST}"
: "${SSH_USER:?set SSH_USER}"
: "${DB_REMOTE_HOST:?set DB_REMOTE_HOST}"
SSH_PORT=${SSH_PORT:-22}
DB_REMOTE_PORT=${DB_REMOTE_PORT:-3306}
case "$SSH_HOST$SSH_USER$DB_REMOTE_HOST" in
  *[!a-zA-Z0-9._:-]*) echo 'Invalid tunnel hostname/user' >&2; exit 1 ;;
esac
case "$SSH_PORT:$DB_REMOTE_PORT" in
  *[!0-9:]*) echo 'Invalid tunnel port' >&2; exit 1 ;;
esac
test -s /run/ssh/id_ed25519
test -s /run/ssh/known_hosts
# 仅 Docker 私有网络可连接此端口；不向宿主机发布 MySQL。
exec ssh -NT -g \
  -o BatchMode=yes -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/run/ssh/known_hosts \
  -o ExitOnForwardFailure=yes -o ConnectTimeout=10 \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -o LogLevel=ERROR \
  -i /run/ssh/id_ed25519 -p "$SSH_PORT" \
  -L "0.0.0.0:3306:${DB_REMOTE_HOST}:${DB_REMOTE_PORT}" \
  "${SSH_USER}@${SSH_HOST}"
