"""隔离验证日志审计与失败回退，不连接服务器或 Docker daemon。"""

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

DEPLOY = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_logs", DEPLOY / "check_logs.py")
check_logs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_logs)
SERVICES = ["api", "tunnel", "web", "worker", "knowledge-worker", "caddy"]


class LogBudgetTests(unittest.TestCase):
    def respond(self, command, text=True):
        if command[1] == "ps":
            return " ".join(SERVICES)
        config = {"Type": "json-file", "Config": {"max-size": "10m", "max-file": "10"}}
        return json.dumps(config) + "|" + command[-1] + "|true"

    def test_full_stack_is_below_one_gb(self):
        with patch.object(
            check_logs.subprocess, "check_output", side_effect=self.respond
        ):
            check_logs.inspect_budget()

    def test_unbounded_logging_is_rejected(self):
        def respond(command, **kwargs):
            if command[1] == "inspect":
                return '{"Type":"json-file","Config":{}}|api|true'
            return "api"

        with (
            patch.object(check_logs.subprocess, "check_output", side_effect=respond),
            self.assertRaisesRegex(SystemExit, "Unexpected logging"),
        ):
            check_logs.inspect_budget()

    def test_extra_containers_can_exceed_aggregate_budget(self):
        def respond(command, **kwargs):
            if command[1] == "ps":
                return " ".join(SERVICES + ["init"] * 4)
            return self.respond(command)

        with (
            patch.object(check_logs.subprocess, "check_output", side_effect=respond),
            self.assertRaisesRegex(SystemExit, "exceeds 1 GB"),
        ):
            check_logs.inspect_budget()


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_is_repeatable_and_preserves_existing_configuration(self):
        with tempfile.TemporaryDirectory(prefix="aihot-bootstrap-") as directory:
            root = Path(directory)
            binary = root / "bin"
            binary.mkdir()
            for tool in ("docker", "flock"):
                fake = binary / tool
                fake.write_text("#!/bin/sh\nexit 0\n")
                fake.chmod(0o700)
            env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}"}
            command = ["bash", str(DEPLOY / "bootstrap.sh"), str(root)]
            subprocess.run(command, env=env, check=True, capture_output=True)
            backend = root / "shared/backend.env"
            backend.write_text("KEEP_EXISTING_CONFIGURATION=yes\n")
            subprocess.run(command, env=env, check=True, capture_output=True)
            self.assertEqual(backend.read_text(), "KEEP_EXISTING_CONFIGURATION=yes\n")
            self.assertTrue((root / "shared/site.env").is_file())
            self.assertTrue((root / "shared/tunnel.env").is_file())
            self.assertTrue((root / "incoming").is_dir())
            self.assertEqual((root / "shared").stat().st_mode & 0o777, 0o700)

    def test_missing_configuration_lists_all_files_and_stops_before_docker(self):
        with tempfile.TemporaryDirectory(prefix="aihot-missing-") as directory:
            root = Path(directory)
            release = "a" * 40
            deploy = root / "releases" / release / "deploy"
            deploy.mkdir(parents=True)
            (deploy / "compose.prod.yaml").write_text("services: {}\n")
            binary = root / "bin"
            binary.mkdir()
            fake = binary / "flock"
            fake.write_text("#!/bin/sh\nexit 0\n")
            fake.chmod(0o700)
            result = subprocess.run(
                ["bash", str(DEPLOY / "deploy.sh"), str(root), release],
                env={**os.environ, "PATH": f"{binary}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 78)
            for filename in (
                "backend.env",
                "site.env",
                "tunnel.env",
                "ssh/id_ed25519",
                "ssh/known_hosts",
            ):
                self.assertIn(f"shared/{filename}", result.stderr)
            self.assertIn("First-time setup is incomplete", result.stderr)


class RollbackTests(unittest.TestCase):
    def test_failed_migration_restores_previous_and_keeps_current(self):
        with tempfile.TemporaryDirectory(prefix="aihot-deploy-") as directory:
            root = Path(directory)
            old, new = "a" * 40, "b" * 40
            for release in (old, new):
                deploy = root / "releases" / release / "deploy"
                deploy.mkdir(parents=True)
                (deploy / "compose.prod.yaml").write_text("services: {}\n")
                shutil.copyfile(
                    DEPLOY / "check_site_config.py", deploy / "check_site_config.py"
                )
            (root / "current").symlink_to(root / "releases" / old)
            shared = root / "shared"
            (shared / "ssh").mkdir(parents=True)
            for filename in (
                "backend.env",
                "site.env",
                "tunnel.env",
                "ssh/id_ed25519",
                "ssh/known_hosts",
            ):
                (shared / filename).write_text("dummy\n")
            binary = root / "bin"
            binary.mkdir()
            if not shutil.which("flock"):
                # macOS 没有 flock 命令；用同样的内核锁语义，仅供隔离测试。
                flock = binary / "flock"
                flock.write_text(
                    "#!/usr/bin/env python3\nimport fcntl, sys\n"
                    "fcntl.flock(int(sys.argv[-1]), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
                )
                flock.chmod(0o700)
            docker = binary / "docker"
            docker.write_text(
                textwrap.dedent("""\
                #!/usr/bin/env python3
                import os, sys, json
                from pathlib import Path
                args = sys.argv[1:]
                with Path(os.environ["OPERATIONS"]).open("a") as stream:
                    stream.write(os.environ["AIHOT_RELEASE"] + " " + " ".join(args) + "\\n")
                if "config" in args and "--format" in args:
                    print(json.dumps({"services": {"caddy": {"environment": {"SITE_PASSWORD_HASH": "$2a$14$" + "A" * 53}}}}))
                if "run" in args and args[-1] == "init":
                    sys.exit(71)
            """)
            )
            docker.chmod(0o700)
            operations = root / "operations"
            result = subprocess.run(
                ["bash", str(DEPLOY / "deploy.sh"), str(root), new],
                env={
                    **os.environ,
                    "PATH": f"{binary}:{os.environ['PATH']}",
                    "OPERATIONS": str(operations),
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 71, result.stderr)
            self.assertEqual(
                (root / "current").resolve(), (root / "releases" / old).resolve()
            )
            commands = operations.read_text().splitlines()
            self.assertTrue(
                any(line.startswith(old) and "up -d" in line for line in commands)
            )
            self.assertFalse(
                any("down" in line or "prune" in line for line in commands)
            )


if __name__ == "__main__":
    unittest.main()
