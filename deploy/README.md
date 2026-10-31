# zhangff.cn 服务器部署

目标：`root@152.136.228.231:22`，域名 `zhangff.cn`。端口、用户名、目录可由 GitHub Variables 覆盖。所有服务和采集在服务器运行，本地电脑关闭不影响采集。生产使用独立的 `deploy/compose.prod.yaml`。

## 首次准备

服务器需要 Linux、Docker Engine、Compose v2.20+、Bash、flock、curl、python3、tar。建议至少 2 核 4 GB，预留源码构建与镜像空间；脚本不会自动修改系统防火墙或安装 Docker。将域名 A 记录指向 `152.136.228.231`；若有 AAAA 记录也必须指向同一服务的有效 IPv6。放行 TCP 80/443、UDP 443（可选 HTTP/3）和部署用 SSH 端口。已有 80/443 服务需先协调入口，本配置不会自动移除其他站点。

先将仓库源码放到服务器临时目录，执行：

```bash
bash deploy/bootstrap.sh /opt/aihot
```

也可先推送代码触发流水线：首次运行会自动创建部署目录和缺失配置模板，已有配置不会覆盖。模板生成后仍需填写以下真实配置，再重跑流水线。缺少文件时会逐项列出路径并以 exit 78 停止，不会启动应用或修改数据库。日志会区分上传目录准备、源码上传与服务器部署阶段。

配置文件仅保留在服务器 `/opt/aihot/shared`，发布代码不会覆盖：

| 文件 | 内容 |
| --- | --- |
| `backend.env` | MySQL 数据库名、用户、密码、GitHub Token、5 GB 数据清理策略等 |
| `site.env` | SITE_DOMAIN=zhangff.cn、ACME_EMAIL |

本地 `backend/.env` 和线上 `/opt/aihot/shared/backend.env` 均使用 MySQL 直连：

```dotenv
MYSQL_HOST=152.136.228.231
MYSQL_PORT=3306
```

保留原数据库名、账号和密码。生产 Compose 不覆盖 MYSQL_HOST/MYSQL_PORT，也不再要求 tunnel.env 或数据库 SSH 密钥。MySQL 必须监听可达地址，账号允许应用来源登录，防火墙/安全组仅放行开发者公网 IP 和生产应用出口 IP。容器中的 127.0.0.1 指向容器自身，不能作为宿主机数据库地址。

已有部署升级前先修改服务器的 backend.env（发布不会覆盖已有配置）。成功执行 `compose up --remove-orphans` 会移除旧 tunnel 容器；旧 tunnel.env 和数据库隧道密钥文件不再使用，可在确认直连正常后自行归档。部署 SSH 密钥仍用于上传和发布，继续保留。

网站公开浏览，无需设置 Caddy 入口密码。在 `shared/backend.env` 配置 `ADMIN_USERNAME=admin` 和至少 12 位的 `ADMIN_PASSWORD`。迁移首次创建管理员，之后环境变量不会覆盖已有密码；通过左下角头像登录后在“用户管理”中重置。旧 `SITE_USER` / `SITE_PASSWORD_HASH` 不再生效。

## GitHub 配置

仓库：`zhangpengfeia/aihot`。在 Settings → Environments 创建 `production`，添加以下 Secrets（也可用 Repository Secrets）。若希望推送后全自动发布，不设置需要人工审核的 environment 规则。

| Secret | 内容 |
| --- | --- |
| `DEPLOY_SSH_KEY` | 登录 root@152.136.228.231 的部署 SSH 私钥；对应公钥已在服务器授权 |
| `DEPLOY_KNOWN_HOSTS` | 已核验的网站服务器 SSH 主机密钥行；非 22 端口用 `[152.136.228.231]:端口` |

可选 Variables：`DEPLOY_HOST`（默认 152.136.228.231）、`DEPLOY_USER`（root）、`DEPLOY_PORT`（22）、`DEPLOY_ROOT`（/opt/aihot）。不能将密码或数据库 Token 填进 Variables。程序数据库密码和 GitHub 采集 Token 留在服务器 `shared/backend.env`，不经过 Actions。

`.github/workflows/deploy.yml` 在 PR 时仅检查；推送 `main` 或从 main 手动触发时先检查、再部署。流水线执行后端检查/测试、前端格式检查/构建、部署配置验证。通过后打包固定提交 SHA 的 `git archive`，SSH 上传并校验 SHA256；不会包含本地未提交文件、`.env`、数据库私钥或 `.git`。服务器构建镜像，所以无需 GHCR 账号或注册表凭据。

构建全部成功后，校验配置与数据库直连 → 暂停采集 → 执行数据库迁移 → 启动 API/Web/两类采集/Caddy → 检查健康状态和日志预算 → 验证公网 HTTPS 无需登录返回 200。最后更新 `current`，保留 `previous` 版本。部署进程通过 flock 串行执行；GitHub 同分支发布不互相取消。版本切换期间可能短暂不可用。

失败时尝试恢复上一次应用版本；数据库迁移、已经提交的数据和自动清理删除不会回滚。首次无历史版本时停止采集进程并保留排障现场。上线前应备份数据库，未来破坏性表结构改动需要另行设计迁移。每次成功后只删除本应用过期源码与镜像，保留当前和上个版本，不执行全局 Docker prune，不影响其他容器。

## 定时采集与日常操作

GitHub worker 每天 **北京时间 00:00** 开始，启动时等待下一个执行点；知识来源每半小时采集。worker 由 Docker restart 策略常驻，服务器重启后 Docker 服务也需要启用。无需 crontab、本地 SSH 隧道或本地 make start。MySQL 的 GET_LOCK 继续防止多进程重复采集。

```bash
ROOT=/opt/aihot
export AIHOT_ROOT="$ROOT" AIHOT_RELEASE_DIR="$(readlink "$ROOT/current")"
export AIHOT_RELEASE="${AIHOT_RELEASE_DIR##*/}"
docker compose -p aihot --env-file "$ROOT/shared/site.env" -f "$AIHOT_RELEASE_DIR/deploy/compose.prod.yaml" ps
docker compose -p aihot --env-file "$ROOT/shared/site.env" -f "$AIHOT_RELEASE_DIR/deploy/compose.prod.yaml" logs --tail=100 -f worker knowledge-worker
# 手动立即采集一轮（临时容器退出后删除）
docker compose -p aihot --env-file "$ROOT/shared/site.env" -f "$AIHOT_RELEASE_DIR/deploy/compose.prod.yaml" run --rm worker python -m app.runtime.github_worker --once
# 审计应用日志预算（不会输出环境变量）
python3 "$AIHOT_RELEASE_DIR/deploy/check_logs.py"
```

## 日志容量

所有生产服务统一使用 Docker `json-file`，`max-size=10m`、`max-file=10`，每容器约 100 MiB。5 个常驻容器 + 最多 1 个迁移容器预算 **600 MiB = 629,145,600 字节 < 1 GB**，为条目边界等留有余量。达到单文件阈值自动轮转并删除最旧文件，迁移容器 `--rm`。本地 Compose 的 5 个容器也设相同轮转，总预算 500 MiB。

API、两类采集、SSH 和 Nginx/Caddy 访问与错误日志仅写标准输出/错误，不额外落入容器文件或宿主机 `.log`。部署脚本不 tee、不创建发布日志，由 GitHub 托管运行器收集其输出。部署会检查所有带 aihot 项目标签的容器的实际日志配置、运行状态及合计预算，超标则失败。

该预算针对**本应用容器日志**，不包含服务器其他程序、宿主机 journal/Docker daemon、外部 MySQL 日志或 GitHub 平台上的流水线日志。不要手工修改 Docker 管理的日志文件；配置对新建容器生效，旧容器需重建。镜像与构建缓存、MySQL 数据、证书卷不是日志，需另留磁盘空间。严格服务器级物理配额需要操作系统统一管理，不能通过本应用 Compose 限制其他服务。

参考：[Docker 日志轮转](https://docs.docker.com/engine/logging/drivers/json-file/)、[Caddy 认证](https://caddyserver.com/docs/caddyfile/directives/basic_auth)、[Caddy HTTPS 代理](https://caddyserver.com/docs/quick-starts/reverse-proxy)。
