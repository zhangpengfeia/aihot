"""验证服务器所有 AIHot 容器的日志预算；仅输出日志配置，不输出容器环境变量。"""

import json
import subprocess


def inspect_budget():
    containers = subprocess.check_output(
        ["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=aihot"],
        text=True,
    ).split()
    if not containers:
        raise SystemExit("No AIHot containers found")
    total = 0
    services = set()
    for container in containers:
        raw = subprocess.check_output(
            [
                "docker",
                "inspect",
                "--format",
                '{{json .HostConfig.LogConfig}}|{{index .Config.Labels "com.docker.compose.service"}}|{{.State.Running}}',
                container,
            ],
            text=True,
        ).strip()
        config, service, running = raw.split("|")
        config = json.loads(config)
        if config != {
            "Type": "json-file",
            "Config": {"max-size": "10m", "max-file": "10"},
        }:
            raise SystemExit(
                f"Unexpected logging configuration for {service}; recreate this container"
            )
        if service != "init" and running != "true":
            raise SystemExit(f"Service is not running: {service}")
        services.add(service)
        total += 10 * 1024**2 * 10
    required = {"tunnel", "api", "web", "worker", "knowledge-worker", "caddy"}
    if not required.issubset(services):
        raise SystemExit(f"Missing services: {sorted(required - services)}")
    if total >= 1_000_000_000:
        raise SystemExit(f"Application log budget exceeds 1 GB: {total} bytes")
    print(
        f"Verified {len(containers)} containers: log budget {total // 1024**2} MiB < 1 GB"
    )


if __name__ == "__main__":
    inspect_budget()
