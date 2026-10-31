"""仅首次建表；已有数据库升级请使用 migrations。"""

from app import models  # noqa: F401 -- 注册全部模型
from app.core.database import Base, get_engine


def main():
    from app.runtime.schema_changes import run_schema_change

    engine = get_engine()
    run_schema_change(engine, lambda: initialize(engine))
    print("MySQL 数据表初始化完成")


def initialize(engine):
    from app.runtime.schema_changes import create_missing_tables

    create_missing_tables(engine, Base.metadata)
    from sqlalchemy.orm import Session

    from app.core.auth import seed_admin
    from app.core.config import get_settings

    with Session(engine) as db:
        seed_admin(db, get_settings())


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
