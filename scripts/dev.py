"""本地开发入口：管理本次启动的服务，退出时一并回收它们的子进程。"""

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def preflight() -> None:
    """启动前统一检查，避免只启动了一半服务才发现配置缺失。"""
    if not (ROOT / "backend/.env").is_file():
        raise RuntimeError(
            "请复制 backend/.env.example 为 backend/.env，填写数据库配置"
        )
    if (
        not shutil.which("npm")
        or not (ROOT / "frontend/node_modules/.bin/vite").is_file()
    ):
        raise RuntimeError("请安装 Node.js / npm，并先执行 make install")
    for port in (8000, 5173):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(
                    f"端口 {port} 不可用，请先停止原来的服务：{exc}"
                ) from exc

    # 使用与 API 相同的配置，只探测 TCP，不读取或输出数据库密码。
    sys.path.insert(0, str(ROOT / "backend"))
    from app.core.config import Settings

    settings = Settings(_env_file=ROOT / "backend/.env")
    try:
        with socket.create_connection((settings.mysql_host, settings.mysql_port), timeout=3):
            pass
    except OSError as exc:
        raise RuntimeError(
            f"无法连接 MySQL：{settings.mysql_host}:{settings.mysql_port}。"
            "请核对 backend/.env 中 MYSQL_HOST/MYSQL_PORT，"
            "确认服务器 MySQL 已启动且允许当前客户端 IP 直连。"
        ) from exc


def stop(children: list[subprocess.Popen]) -> None:
    # 每个服务独立进程组，npm 启动的 Vite 也会收到信号；不触碰其他项目进程。
    for child in children:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and any(
        child.poll() is None for child in children
    ):
        time.sleep(0.1)
    for child in children:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()


def main() -> int:
    children: list[subprocess.Popen] = []
    stopping = False

    def request_stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        preflight()
        services = [
            (
                "API",
                "backend",
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
            ),
            (
                "前端",
                "frontend",
                ["npm", "run", "dev", "--", "--port", "5173", "--strictPort"],
            ),
        ]
        for name, directory, command in services:
            if stopping:
                return 0
            children.append(
                subprocess.Popen(command, cwd=ROOT / directory, start_new_session=True)
            )
            print(f"已启动 {name}（PID {children[-1].pid}）", flush=True)
        print(
            "前端：http://127.0.0.1:5173  API 文档：http://127.0.0.1:8000/docs",
            flush=True,
        )
        print(
            "本地启动不执行采集。按 Ctrl+C 停止前端和 API。", flush=True
        )
        while not stopping:
            for (name, _, _), child in zip(services, children, strict=True):
                code = child.poll()
                if code is not None:
                    print(
                        f"{name} 已退出（退出码 {code}），停止其余服务。",
                        file=sys.stderr,
                    )
                    return code if code > 0 else 1
            time.sleep(0.3)
        return 0
    except (OSError, RuntimeError) as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
        return 1
    finally:
        stop(children)


if __name__ == "__main__":
    raise SystemExit(main())
