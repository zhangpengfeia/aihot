#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root=${1:-/opt/aihot}
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
[[ $root =~ ^/[a-zA-Z0-9_/-]+$ && $root != / && $root != *..* ]] || { echo 'Invalid deployment root' >&2; exit 1; }
for tool in docker flock curl python3 tar; do
  command -v "$tool" >/dev/null || { echo "Missing server dependency: $tool. Install it before retrying deployment." >&2; exit 1; }
done
docker compose version
mkdir -p "$root"/{shared,incoming,releases}
chmod 700 "$root/shared" "$root/incoming"
for entry in backend site; do
  if [[ ! -e $root/shared/$entry.env ]]; then
    if [[ $entry == backend ]]; then
      cp "$source_dir/backend/.env.example" "$root/shared/$entry.env"
    else
      cp "$source_dir/deploy/templates/$entry.env.example" "$root/shared/$entry.env"
    fi
    chmod 600 "$root/shared/$entry.env"
  fi
done
cat <<EOF
Prepared $root (existing configuration was preserved).
Fill shared/backend.env (direct MySQL host/port) and shared/site.env.
No containers have been started and no database has been changed.
EOF
