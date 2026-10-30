#!/usr/bin/env bash
# 仅用于数据库与部署应用位于同一台服务器的情况；保留已有密钥及 SSH 授权。
set -Eeuo pipefail
umask 077
root=${1:-/opt/aihot}
[[ $root =~ ^/[a-zA-Z0-9_/-]+$ && $root != / && $root != *..* ]]
[[ $(id -u) == 0 ]] || { echo 'Run this helper as root on the database server.' >&2; exit 1; }
config=$root/shared/tunnel.env
[[ -s $config ]] || { echo "Missing $config" >&2; exit 1; }
value() { awk -F= -v name="$1" '$1 == name {print substr($0, index($0, "=")+1)}' "$config" | tr -d '\r'; }
host=$(value SSH_HOST)
user=$(value SSH_USER)
ssh_port=$(value SSH_PORT)
db_host=$(value DB_REMOTE_HOST)
db_port=$(value DB_REMOTE_PORT)
ssh_port=${ssh_port:-22}
db_port=${db_port:-3306}
gateway=$(docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}')
[[ $gateway =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Cannot determine Docker host gateway.' >&2; exit 1; }
[[ $host == 127.0.0.1 || $host == localhost || $host == "$gateway" ]] || { echo 'SSH_HOST is not local; configure the remote bastion separately.' >&2; exit 1; }
[[ $user == root && ( $db_host == 127.0.0.1 || $db_host == localhost ) ]] || { echo 'This helper only supports local root SSH and loopback MySQL.' >&2; exit 1; }
[[ $ssh_port =~ ^[0-9]+$ && $db_port =~ ^[0-9]+$ ]]
[[ $ssh_port -ge 1 && $ssh_port -le 65535 && $db_port -ge 1 && $db_port -le 65535 ]]
mkdir -p "$root/shared/ssh" /root/.ssh
chmod 700 "$root/shared/ssh" /root/.ssh
exec 9>"$root/tunnel-setup.lock"
flock -n 9 || { echo 'Tunnel setup is already running.' >&2; exit 1; }
key=$root/shared/ssh/id_ed25519
if [[ ! -e $key ]]; then
  ssh-keygen -q -t ed25519 -N '' -C aihot-database-tunnel -f "$key"
fi
chmod 600 "$key"
ssh-keygen -y -P '' -f "$key" > "$key.pub"
read -r key_type key_body < "$key.pub"
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
# 禁止交互命令及其他 SSH 功能，只允许连接指定数据库目标。
if ! grep -Fq "$key_body" /root/.ssh/authorized_keys; then
  printf '\nrestrict,port-forwarding,permitopen="%s:%s",command="/bin/false" %s %s aihot-database-tunnel\n' \
    "$db_host" "$db_port" "$key_type" "$key_body" >> /root/.ssh/authorized_keys
fi
# 从已验证服务器本地读取公钥，不临时信任未经核验的 ssh-keyscan 结果。
known_name=$gateway
[[ $ssh_port == 22 ]] || known_name="[$gateway]:$ssh_port"
read -r host_type host_body _ < /etc/ssh/ssh_host_ed25519_key.pub
known=$root/shared/ssh/known_hosts
touch "$known"
chmod 600 "$known"
entry="$known_name $host_type $host_body"
grep -Fxq "$entry" "$known" || printf '%s\n' "$entry" >> "$known"
temp_config=$(mktemp "$root/shared/tunnel.env.XXXXXX")
trap 'rm -f -- "$temp_config"' EXIT
awk -v gateway="$gateway" '/^SSH_HOST=/ {$0="SSH_HOST=" gateway} {print}' "$config" > "$temp_config"
chmod 600 "$temp_config"
mv "$temp_config" "$config"
echo "Local database tunnel configured: SSH $gateway:$ssh_port -> $db_host:$db_port. Existing deployment authorization and private keys were preserved."
