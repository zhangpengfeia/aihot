#!/usr/bin/env bash
# 服务器入口：bash deploy/deploy.sh /opt/aihot <完整提交SHA>
set -Eeuo pipefail
umask 077
root=${1:-/opt/aihot}
release=${2:?provide full commit SHA}
[[ $root =~ ^/[a-zA-Z0-9_/-]+$ && $root != / && $root != *..* ]] || { echo 'Invalid deployment root' >&2; exit 1; }
[[ $release =~ ^[a-f0-9]{40}$ ]] || { echo 'Invalid release SHA' >&2; exit 1; }
release_dir=$root/releases/$release
[[ -f $release_dir/deploy/compose.prod.yaml ]] || { echo 'Missing release files' >&2; exit 1; }
command -v flock >/dev/null
command -v curl >/dev/null
command -v python3 >/dev/null
exec 9>"$root/deploy.lock"
flock -n 9 || { echo 'Another deployment is running' >&2; exit 1; }
missing=0
for file in backend.env site.env; do
  if [[ ! -s $root/shared/$file ]]; then
    echo "Missing server configuration: $root/shared/$file" >&2
    missing=1
  fi
done
if (( missing )); then
  echo "First-time setup is incomplete. Fill $root/shared/backend.env, site.env with the direct MySQL endpoint. Then rerun the workflow." >&2
  exit 78
fi
chmod 700 "$root/shared"
chmod 600 "$root/shared/"*.env
export AIHOT_ROOT=$root AIHOT_RELEASE=$release AIHOT_RELEASE_DIR=$release_dir
previous=$(readlink "$root/current" || true)
compose() {
  docker compose --project-name aihot --env-file "$root/shared/site.env" \
    -f "$AIHOT_RELEASE_DIR/deploy/compose.prod.yaml" "$@"
}
rollback() {
  local result=$?
  trap - ERR
  echo 'Deployment failed; restoring the previous application version if available.' >&2
  if [[ $previous == "$root/releases/"* && -f $previous/deploy/compose.prod.yaml ]]; then
    export AIHOT_RELEASE_DIR=$previous AIHOT_RELEASE=${previous##*/}
    compose up -d --remove-orphans --wait --wait-timeout 180 || true
  else
    # 首次发布失败：停止工作进程，避免继续写入；保留现场供排查。
    compose stop worker knowledge-worker || true
  fi
  echo 'Database migrations and already committed data are not rolled back.' >&2
  exit "$result"
}
compose --profile tools config --quiet
# 在改动正在运行的服务之前完成构建；全部输出由调用方终端/Actions 接收，不写日志文件。
compose build --pull api web
compose run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
trap rollback ERR
# 预检与迁移容器均 --rm；不会累积 stopped 容器日志。
compose run --rm --no-deps init python -c \
  'from app.core.config import get_settings; s=get_settings(); assert s.github_token, "Set GITHUB_TOKEN in shared/backend.env"; assert s.mysql_password and not s.mysql_password.startswith("replace-"), "Configure database password"; from app.core.database import get_engine; from sqlalchemy import text; c=get_engine().connect(); c.execute(text("SELECT 1")); c.close()'
compose stop worker knowledge-worker
compose run --rm --no-deps init
compose up -d --remove-orphans --wait --wait-timeout 180 api web worker knowledge-worker caddy
# 给 worker 留出启动时间，检查没有立即退出，并检查所有应用容器的日志预算。
sleep 3
python3 "$release_dir/deploy/check_logs.py"
domain=$(compose exec -T caddy printenv SITE_DOMAIN | tr -d '\r\n')
[[ $domain =~ ^[a-zA-Z0-9.-]+$ ]] || { echo 'Invalid domain' >&2; false; }
ready=0
for _ in $(seq 1 24); do
  # 公开访问应返回 200；同时验证域名、证书和公网入口，避免误报部署成功。
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "https://$domain/" || true)
  if [[ $code == 200 ]]; then ready=1; break; fi
  sleep 5
done
[[ $ready == 1 ]] || { echo 'HTTPS/domain/public-access verification failed' >&2; false; }
if [[ -n $previous && $previous != "$release_dir" ]]; then
  ln -sfn "$previous" "$root/previous"
fi
ln -sfn "$release_dir" "$root/current"
trap - ERR
# 只清理本应用过期发布和镜像，保留 current/previous，不执行全局 docker prune。
keep_previous=$(readlink "$root/previous" || true)
for directory in "$root/releases/"*; do
  [[ -d $directory && ${directory##*/} =~ ^[a-f0-9]{40}$ ]] || continue
  [[ $directory != "$release_dir" && $directory != "$keep_previous" ]] || continue
  old=${directory##*/}
  docker image rm "aihot-backend:$old" "aihot-web:$old" "aihot-tunnel:$old" >/dev/null 2>&1 || true
  rm -rf -- "$directory"
done
echo "Deployed $release to https://$domain; GitHub collection runs at 00:00 Asia/Shanghai."
