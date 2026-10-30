"""来源地址的稳定身份；无需初始化数据库或应用。"""

import hashlib


def source_key(url):
    return hashlib.sha256(str(url).encode()).hexdigest()
