"""无需 Docker daemon 的生产配置检查，只使用临时假凭据，绝不读取真实 .env。"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from check_site_config import valid_exported_hash

REPO = Path(__file__).resolve().parents[1]


def validate():
    with tempfile.TemporaryDirectory(prefix="aihot-compose-") as directory:
        root = Path(directory)
        shared = root / "shared"
        (shared / "ssh").mkdir(parents=True)
        (shared / "backend.env").write_text(
            "MYSQL_PASSWORD=dummy\nGITHUB_TOKEN=dummy\n"
        )
        (shared / "tunnel.env").write_text(
            "SSH_HOST=example.com\nSSH_USER=dummy\nDB_REMOTE_HOST=127.0.0.1\n"
        )
        (shared / "site.env").write_text(
            "ACME_EMAIL=dummy@example.com\nSITE_USER=dummy\nSITE_PASSWORD_HASH='$2a$14$"
            + "A" * 53
            + "'\n"
        )
        env = {
            **os.environ,
            "AIHOT_ROOT": str(root),
            "AIHOT_RELEASE": "0" * 40,
            "AIHOT_RELEASE_DIR": str(REPO),
        }
        raw = subprocess.check_output(
            [
                "docker",
                "compose",
                "--env-file",
                str(shared / "site.env"),
                "-f",
                str(REPO / "deploy/compose.prod.yaml"),
                "--profile",
                "tools",
                "config",
                "--format",
                "json",
            ],
            env=env,
            text=True,
        )
        services = json.loads(raw)["services"]
        assert valid_exported_hash(
            services["caddy"]["environment"]["SITE_PASSWORD_HASH"]
        )
    assert set(services) == {
        "tunnel",
        "init",
        "api",
        "worker",
        "knowledge-worker",
        "web",
        "caddy",
    }
    for name, service in services.items():
        assert service["logging"] == {
            "driver": "json-file",
            "options": {"max-size": "10m", "max-file": "10"},
        }, name
        if name != "caddy":
            assert not service.get("ports"), f"Unexpected public port: {name}"
    for name in ("api", "init", "worker", "knowledge-worker"):
        assert services[name]["environment"]["MYSQL_HOST"] == "tunnel"
        assert services[name]["environment"]["MYSQL_PORT"] == "3306"
    assert services["worker"]["command"] == [
        "python",
        "-m",
        "app.runtime.github_worker",
    ]
    assert services["knowledge-worker"]["command"] == [
        "python",
        "-m",
        "app.runtime.knowledge_worker",
    ]
    assert len(services) * 10 * 1024**2 * 10 < 1_000_000_000
    print(
        "Production Compose validated: 7 services, 700 MiB log budget, no public database/API ports"
    )


if __name__ == "__main__":
    validate()
