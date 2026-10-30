"""兼容命令入口，实际实现位于 app.runtime.github_worker。"""

from app.runtime.github_worker import main

if __name__ == "__main__":
    main()
