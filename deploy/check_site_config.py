"""检查 Compose 解析后的认证配置；只输出状态，不输出凭据。"""

import json
import re
import sys

BCRYPT = re.compile(r"\$2[aby]\$(?:0[4-9]|[12]\d|3[01])\$[./A-Za-z0-9]{53}")


def valid_hash(value):
    return isinstance(value, str) and BCRYPT.fullmatch(value) is not None


def valid_exported_hash(value):
    # Compose 为使导出模型可再次作为 Compose 输入，将字面量 $ 写成 $$。
    # 只在 config 导出边界还原一层；原始配置及密码生成器仍使用严格校验。
    return valid_hash(value.replace("$$", "$")) if isinstance(value, str) else False


def main():
    try:
        config = json.load(sys.stdin)
        password_hash = config["services"]["caddy"]["environment"]["SITE_PASSWORD_HASH"]
    except (ValueError, KeyError, TypeError):
        raise SystemExit("Cannot read Caddy authentication configuration") from None
    if not valid_exported_hash(password_hash):
        raise SystemExit(
            "SITE_PASSWORD_HASH must be a complete 60-character bcrypt hash, not a plaintext password. "
            "Run: python3 deploy/set-site-password.py /opt/aihot/shared/site.env; then rerun deployment. "
            "If editing manually, enclose the complete hash in single quotes."
        )
    print("Website password hash format verified (credentials hidden)")


if __name__ == "__main__":
    main()
