"""迁移互斥、定向重试及失败释放锁的边界。"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

from app.runtime import schema_changes


def engine_mock(acquired=1):
    engine = MagicMock()
    engine.dialect.name = "mysql"
    engine.url.database = "aihot_test"
    connection = engine.connect.return_value.__enter__.return_value
    connection.scalar.return_value = acquired
    return engine, connection


def error(code):
    return OperationalError("DESCRIBE example", {}, Exception(code, "test"))


def test_retries_1684_under_one_lock(monkeypatch):
    engine, connection = engine_mock()
    operation = MagicMock(side_effect=[error(1684), error(1684), "done"])
    sleep = MagicMock()
    monkeypatch.setattr(schema_changes.time, "sleep", sleep)
    assert schema_changes.run_schema_change(engine, operation) == "done"
    assert operation.call_count == 3
    assert connection.scalar.call_count == 1
    assert connection.execute.call_count == 1
    assert "RELEASE_LOCK" in str(connection.execute.call_args.args[0])
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]


def test_lock_timeout_does_not_start_migration():
    engine, connection = engine_mock(0)
    operation = MagicMock()
    with pytest.raises(RuntimeError, match="make migrate"):
        schema_changes.run_schema_change(engine, operation)
    operation.assert_not_called()
    connection.execute.assert_not_called()


@pytest.mark.parametrize("code,attempts", [(1684, 4), (1045, 1), (1064, 1)])
def test_retry_limit_and_unrelated_errors_release_lock(monkeypatch, code, attempts):
    engine, connection = engine_mock()
    operation = MagicMock(side_effect=error(code))
    monkeypatch.setattr(schema_changes.time, "sleep", lambda _: None)
    with pytest.raises(OperationalError):
        schema_changes.run_schema_change(engine, operation)
    assert operation.call_count == attempts
    assert connection.execute.call_count == 1


def test_release_failure_discards_connection():
    engine, connection = engine_mock()
    connection.execute.side_effect = error(2013)
    assert schema_changes.run_schema_change(engine, lambda: "done") == "done"
    connection.invalidate.assert_called_once()


def test_other_dialects_do_not_use_mysql_locks():
    engine = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    assert schema_changes.run_schema_change(engine, lambda: "done") == "done"


def test_metadata_lock_timeout_stops_without_retry(monkeypatch):
    engine, connection = engine_mock()
    operation = MagicMock(side_effect=error(1205))
    sleep = MagicMock()
    monkeypatch.setattr(schema_changes.time, "sleep", sleep)
    with pytest.raises(RuntimeError, match="旧事务"):
        schema_changes.run_schema_change(engine, operation)
    operation.assert_called_once()
    sleep.assert_not_called()
    assert connection.execute.call_count == 1


def test_mysql_creates_only_missing_tables_without_describe(monkeypatch):
    engine, _ = engine_mock()
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["users"]
    inspector.get_view_names.return_value = ["existing_view"]
    monkeypatch.setattr(schema_changes, "inspect", lambda _: inspector)
    users = SimpleNamespace(name="users")
    dashboard = SimpleNamespace(name="dashboard_preferences")
    view = SimpleNamespace(name="existing_view")
    metadata = SimpleNamespace(sorted_tables=[users, dashboard, view], create_all=MagicMock())
    schema_changes.create_missing_tables(engine, metadata)
    metadata.create_all.assert_called_once_with(engine, tables=[dashboard], checkfirst=False)


def test_mysql_no_missing_tables_does_not_issue_ddl(monkeypatch):
    engine, _ = engine_mock()
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["users"]
    inspector.get_view_names.return_value = []
    monkeypatch.setattr(schema_changes, "inspect", lambda _: inspector)
    metadata = SimpleNamespace(
        sorted_tables=[SimpleNamespace(name="users")], create_all=MagicMock()
    )
    schema_changes.create_missing_tables(engine, metadata)
    metadata.create_all.assert_not_called()


def test_database_connections_have_server_metadata_timeout(monkeypatch):
    from app.core import database

    database.get_engine.cache_clear()
    create = MagicMock()
    monkeypatch.setattr(database, "create_engine", create)
    try:
        database.get_engine()
        options = create.call_args.kwargs["connect_args"]
        assert options["init_command"] == "SET SESSION lock_wait_timeout=10"
        assert options["read_timeout"] > 10
    finally:
        database.get_engine.cache_clear()
