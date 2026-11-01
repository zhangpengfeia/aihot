"""部署前验证直连配置，只输出地址和错误码，不输出凭据。"""

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.database import get_engine


def check_database(settings, engine_factory=get_engine):
    if not settings.github_token:
        raise RuntimeError("Set GITHUB_TOKEN in shared/backend.env")
    if not settings.mysql_password or settings.mysql_password.startswith("replace-"):
        raise RuntimeError("Configure MYSQL_PASSWORD in shared/backend.env")
    if settings.mysql_host.strip().lower() in {"localhost", "127.0.0.1", "::1", "[::1]"}:
        raise RuntimeError(
            "shared/backend.env still uses a loopback MYSQL_HOST. Inside the new container this "
            "points to the container itself; the old SSH tunnel is no longer used. "
            "Set MYSQL_HOST and MYSQL_PORT to the real MySQL endpoint reachable from Docker "
            "(for this deployment, verify 152.136.228.231:3306), then rerun deployment. "
            "Existing server configuration is preserved and is not overwritten automatically."
        )
    try:
        with engine_factory().connect() as connection:
            connection.execute(text("SELECT 1"))
    except DBAPIError as exc:
        code = exc.orig.args[0] if exc.orig.args else "unknown"
        raise RuntimeError(
            f"MySQL preflight failed: {settings.mysql_host}:{settings.mysql_port}, code={code}. "
            "Check shared/backend.env, database listener, firewall and Docker connectivity."
        ) from None
    print("Direct MySQL connection verified (credentials hidden)")


def main():
    try:
        check_database(get_settings())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
