"""交互设置网站密码：明文仅经 stdin 传给 Caddy，配置只保存哈希。"""

import getpass
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from check_site_config import valid_hash


def write_hash(path, password_hash):
    if not valid_hash(password_hash):
        raise ValueError("Invalid bcrypt hash; configuration was not changed")
    lines = path.read_text().splitlines()
    entry = f"SITE_PASSWORD_HASH='{password_hash}'"
    output = []
    replaced = False
    for line in lines:
        if re.match(r"^\s*SITE_PASSWORD_HASH\s*=", line):
            if not replaced:
                output.append(entry)
                replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(entry)
    descriptor, name = tempfile.mkstemp(prefix=".site-password-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write("\n".join(output) + "\n")
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/aihot/shared/site.env")
    if not path.is_file():
        raise SystemExit("site.env is missing; run bootstrap first")
    password = getpass.getpass("Website password (hidden): ")
    confirmation = getpass.getpass("Confirm website password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match; configuration was not changed")
    if (
        not password
        or len(password.encode("utf-8")) > 72
        or password != password.strip()
    ):
        raise SystemExit("Use 1-72 UTF-8 bytes with no leading/trailing whitespace")
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "--log-driver",
            "none",
            "caddy:2-alpine",
            "caddy",
            "hash-password",
            "--algorithm",
            "bcrypt",
        ],
        input=password + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    hashes = [
        line.strip() for line in result.stdout.splitlines() if valid_hash(line.strip())
    ]
    if result.returncode or len(hashes) != 1:
        raise SystemExit(
            "Caddy could not generate a bcrypt hash; configuration was not changed"
        )
    write_hash(path, hashes[0])
    print(
        "Website password saved as a bcrypt hash with mode 600. Rerun deployment to apply it."
    )


if __name__ == "__main__":
    main()
