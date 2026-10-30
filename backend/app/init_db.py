"""首次安装时显式创建表；不在 Web 启动时隐式改动数据库。"""

from app import models  # noqa: F401 -- 将模型注册到 metadata
from app.db import Base, get_engine

if __name__ == "__main__":
    Base.metadata.create_all(get_engine())
    from sqlalchemy.orm import Session

    from app.config import get_settings
    from app.knowledge_management import seed_sources

    with Session(get_engine()) as session:
        seed_sources(session, get_settings())
        session.commit()
    print("MySQL 数据表初始化完成")
