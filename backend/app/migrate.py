"""兼容命令入口，实际实现位于 app.runtime.migrations。"""

from app.core.database import get_engine
from app.runtime.migrations import migrate

if __name__ == "__main__":
    migrate(get_engine())
    print("数据库结构升级完成")
