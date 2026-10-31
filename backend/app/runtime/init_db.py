"""仅首次建表；已有数据库升级请使用 migrations。"""

from app import models  # noqa: F401 -- 注册全部模型
from app.core.database import Base, get_engine


def main():
    Base.metadata.create_all(get_engine())
    from sqlalchemy.orm import Session

    from app.core.auth import seed_admin
    from app.core.config import get_settings

    with Session(get_engine()) as db:
        seed_admin(db, get_settings())
    print("MySQL 数据表初始化完成")


if __name__ == "__main__":
    main()
