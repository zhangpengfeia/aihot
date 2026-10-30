# zhangff.cn 服务器部署

目标：`root@152.136.228.231:22`，域名 `zhangff.cn`。端口、用户名、目录可由 GitHub Variables 覆盖。所有服务和采集在服务器运行，本地电脑关闭不影响采集。生产使用独立的 `deploy/compose.prod.yaml`。

## 首次准备

服务器需要 Linux、Docker Engine、Compose v2.20+、Bash、flock、curl、python3、tar。建议至少 2 核 4 GB，预留源码构建与镜像空间；脚本不会自动修改系统防火墙或安装 Docker。将域名 A 记录指向 `152.136.228.231`；若有 AAAA 记录也必须指向同一服务的有效 IPv6。放行 TCP 80/443、UDP 443（可选 HTTP/3）和部署用 SSH 端口。已有 80/443 服务需先协调入口，本配置不会自动移除其他站点。

先将仓库源码放到服务器临时目录，执行：

```bash
bash deploy/bootstrap.sh /opt/aihot
```

也可先推送代码触发流水线：首次运行会自动创建部署目录和缺失配置模板，已有配置不会覆盖。模板生成后仍需填写以下真实配置及安装隧道密钥，再重跑流水线。缺少文件时会逐项列出路径并以 exit 78 停止，不会启动应用或修改数据库。日志会区分上传目录准备、源码上传与服务器部署阶段。

配置文件仅保留在服务器 `/opt/aihot/shared`，发布代码不会覆盖：

| 文件 | 内容 |
| --- | --- |
| `backend.env` | MySQL 数据库名、用户、密码、GitHub Token、5 GB 数据清理策略等 |
| `tunnel.env` | 数据库堡垒机 SSH_HOST/SSH_PORT/SSH_USER，及从堡垒机访问的数据库 DB_REMOTE_HOST/DB_REMOTE_PORT |
| `site.env` | SITE_DOMAIN=zhangff.cn、ACME_EMAIL、登录用户名和 bcrypt 密码哈希 |
| `ssh/id_ed25519` | 服务器到数据库堡垒机的专用 SSH 私钥，权限 600；不支持交互密码或带口令的密钥 |
| `ssh/known_hosts` | 经核验的数据库堡垒机主机密钥，非 22 端口使用 `[host]:port` 格式 |

`backend.env` 中 MYSQL_HOST/MYSQL_PORT 在生产 Compose 中固定覆盖为 `tunnel:3306`，不要填宿主机的 `127.0.0.1:13306`。其他数据库配置不变。SSH 隧道只向容器网络开放 3306，不发布到公网；保持存活、断线退出后由 Docker 自动重启。数据库若就在该网站服务器上，也可将 SSH_HOST 配成 `152.136.228.231`、SSH_USER=root、DB_REMOTE_HOST=127.0.0.1；请先确认数据库确在该位置并已授权专用隧道公钥。

用 Caddy 交互生成登录密码哈希（不要将明文密码写进命令或仓库）：

```bash
docker run --rm -it --log-driver none caddy:2-alpine caddy hash-password
```

将输出填入 `site.env` 的 `SITE_PASSWORD_HASH='完整哈希'`，保留单引号以防 dotenv 展开 `$`。HTTPS 证书由 Caddy 自动申请及续期。全站（含 API 文档）使用 Basic Auth，因为该项目的收藏、备注和管理操作属于共享个人实例。不要将初始化示例值用于生产。

部署私钥和数据库隧道私钥是两套用途。隧道公钥在数据库堡垒机授权，建议限制为目标数据库地址转发；部署公钥在网站服务器授权。获取 SSH 主机密钥后，应通过云控制台/可信渠道核对指纹再保存，流水线和隧道均启用 StrictHostKeyChecking，不临时信任扫描结果。

## GitHub 配置

仓库：`zhangpengfeia/aihot`。在 Settings → Environments 创建 `production`，添加以下 Secrets（也可用 Repository Secrets）。若希望推送后全自动发布，不设置需要人工审核的 environment 规则。

| Secret | 内容 |
| --- | --- |
| `DEPLOY_SSH_KEY` | 登录 root@152.136.228.231 的部署 SSH 私钥；对应公钥已在服务器授权 |
| `DEPLOY_KNOWN_HOSTS` | 已核验的网站服务器 SSH 主机密钥行；非 22 端口用 `[152.136.228.231]:端口` |

可选 Variables：`DEPLOY_HOST`（默认 152.136.228.231）、`DEPLOY_USER`（root）、`DEPLOY_PORT`（22）、`DEPLOY_ROOT`（/opt/aihot）。不能将密码或数据库 Token 填进 Variables。程序数据库密码和 GitHub 采集 Token 留在服务器 `shared/backend.env`，不经过 Actions。

`.github/workflows/deploy.yml` 在 PR 时仅检查；推送 `main` 或从 main 手动触发时先检查、再部署。流水线执行后端检查/测试、前端格式检查/构建、部署配置验证。通过后打包固定提交 SHA 的 `git archive`，SSH 上传并校验 SHA256；不会包含本地未提交文件、`.env`、数据库私钥或 `.git`。服务器构建镜像，所以无需 GHCR 账号或注册表凭据。

构建全部成功后，启动隧道 → 校验必要配置 → 暂停采集 → 执行数据库迁移 → 启动 API/Web/两类采集/Caddy → 检查健康状态和日志预算 → 验证公网 HTTPS 返回认证要求。最后更新 `current`，保留 `previous` 版本。部署进程通过 flock 串行执行；GitHub 同分支发布不互相取消。版本切换期间可能短暂不可用。

失败时尝试恢复上一次应用版本；数据库迁移、已经提交的数据和自动清理删除不会回滚。首次无历史版本时停止采集进程并保留排障现场。上线前应备份数据库，未来破坏性表结构改动需要另行设计迁移。每次成功后只删除本应用过期源码与镜像，保留当前和上个版本，不执行全局 Docker prune，不影响其他容器。

## 定时采集与日常操作

GitHub worker 每天 **北京时间 00:00** 开始，启动时等待下一个执行点；知识来源每半小时采集。worker 由 Docker restart 策略常驻，服务器重启后 Docker 服务也需要启用。无需 crontab、本地 SSH 隧道或本地 make start。MySQL 的 GET_LOCK 继续防止多进程重复采集。

```bash
ROOT=/opt/aihot
export AIHOT_ROOT="$ROOT" AIHOT_RELEASE_DIR="$(readlink "$ROOT/current")"
export AIHOT_RELEASE="${AIHOT_RELEASE_DIR##*/}"
docker compose -p aihot --env-file "$ROOT/shared/site.env" -f "$AIHOT_RELEASE_DIR/deploy/compose.prod.yaml" ps
docker compose -p aihot --env-file "$ROOT/shared/site.env" -f "$AIHOT_RELEASE_DIR/deploy/compose.prod.yaml" logs --tail=100 -f worker knowledge-worker tunnel
# 手动立即采集一轮（临时容器退出后删除）
docker compose -p aihot --env-file "$ROOT/shared/site.env" -f "$AIHOT_RELEASE_DIR/deploy/compose.prod.yaml" run --rm worker python -m app.runtime.github_worker --once
# 审计应用日志预算（不会输出环境变量）
python3 "$AIHOT_RELEASE_DIR/deploy/check_logs.py"
```

## 日志容量

所有生产服务统一使用 Docker `json-file`，`max-size=10m`、`max-file=10`，每容器约 100 MiB。6 个常驻容器 + 最多 1 个迁移容器预算 **700 MiB = 734,003,200 字节 < 1 GB**，为条目边界等留有余量。达到单文件阈值自动轮转并删除最旧文件，迁移容器 `--rm`。本地 Compose 的 5 个容器也设相同轮转，总预算 500 MiB。

API、两类采集、SSH 和 Nginx/Caddy 访问与错误日志仅写标准输出/错误，不额外落入容器文件或宿主机 `.log`。部署脚本不 tee、不创建发布日志，由 GitHub 托管运行器收集其输出。部署会检查所有带 aihot 项目标签的容器的实际日志配置、运行状态及合计预算，超标则失败。

该预算针对**本应用容器日志**，不包含服务器其他程序、宿主机 journal/Docker daemon、外部 MySQL 日志或 GitHub 平台上的流水线日志。不要手工修改 Docker 管理的日志文件；配置对新建容器生效，旧容器需重建。镜像与构建缓存、MySQL 数据、证书卷不是日志，需另留磁盘空间。严格服务器级物理配额需要操作系统统一管理，不能通过本应用 Compose 限制其他服务。

参考：[Docker 日志轮转](https://docs.docker.com/engine/logging/drivers/json-file/)、[Caddy 认证](https://caddyserver.com/docs/caddyfile/directives/basic_auth)、[Caddy HTTPS 代理](https://caddyserver.com/docs/quick-starts/reverse-proxy)。
