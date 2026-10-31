-- 由具备 PROCESS 和 performance_schema 查询权限的数据库管理员执行。
-- 仅读取锁与事务元数据，不结束连接，不修改业务数据。
SELECT object_schema, object_name, waiting_pid, blocking_pid, waiting_query_secs
FROM sys.schema_table_lock_waits
WHERE object_schema = DATABASE();

SELECT trx_mysql_thread_id, trx_started, trx_state, trx_tables_locked
FROM information_schema.innodb_trx
ORDER BY trx_started;
