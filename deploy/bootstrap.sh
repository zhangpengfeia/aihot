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
mkdir -p "$root"/{shared/ssh,incoming,releases}
chmod 700 "$root/shared" "$root/shared/ssh" "$root/incoming"
for entry in backend site tunnel; do
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
Fill shared/backend.env, shared/site.env, shared/tunnel.env.
Install the database SSH private key as shared/ssh/id_ed25519 (chmod 600).
Install VERIFIED database SSH host keys as shared/ssh/known_hosts.
No containers have been started and no database has been changed.
EOF
