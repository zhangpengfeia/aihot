"""无需 Docker daemon 的生产配置检查，只使用临时假凭据，绝不读取真实 .env。"""

import json
import os
import subprocess
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def validate():
    with tempfile.TemporaryDirectory(prefix="aihot-compose-") as directory:
        root = Path(directory)
        shared = root / "shared"
        shared.mkdir()
        (shared / "backend.env").write_text(
            "MYSQL_HOST=192.0.2.10\nMYSQL_PORT=3307\nMYSQL_PASSWORD=dummy\nGITHUB_TOKEN=dummy\n"
        )
        (shared / "site.env").write_text("ACME_EMAIL=dummy@example.com\n")
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
        assert "SITE_PASSWORD_HASH" not in services["caddy"]["environment"]
    assert set(services) == {
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
        assert services[name]["environment"]["MYSQL_HOST"] == "192.0.2.10"
        assert services[name]["environment"]["MYSQL_PORT"] == "3307"
        assert services[name]["tmpfs"] == ["/tmp:size=64m,mode=1777"], name
    for name, service in services.items():
        for mount in service.get("tmpfs", []):
            assert mount.split(":", 1)[0].startswith("/"), f"Invalid tmpfs path: {name}"
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
        "Production Compose validated: 6 services, 600 MiB log budget, no public database/API ports"
    )


if __name__ == "__main__":
    validate()
