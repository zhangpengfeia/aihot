from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

from app.runtime.check_database import check_database


def settings(host="mysql.internal"):
    return SimpleNamespace(
        mysql_host=host,
        mysql_port=3306,
        mysql_password="private-secret",
        github_token="private-token",
    )


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1", "[::1]"])
def test_old_tunnel_endpoint_is_rejected_before_connecting(host):
    engine = MagicMock()
    with pytest.raises(RuntimeError, match="old SSH tunnel"):
        check_database(settings(host), engine)
    engine.assert_not_called()


def test_valid_direct_endpoint_is_probed():
    factory = MagicMock()
    check_database(settings(), factory)
    factory.return_value.connect.return_value.__enter__.return_value.execute.assert_called_once()


def test_connection_error_hides_password_and_token():
    factory = MagicMock(
        side_effect=OperationalError("", {}, Exception(2003, "private-secret private-token"))
    )
    with pytest.raises(RuntimeError) as error:
        check_database(settings(), factory)
    assert "code=2003" in str(error.value)
    assert "private-secret" not in str(error.value)
    assert "private-token" not in str(error.value)
