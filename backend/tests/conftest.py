"""迁移测试使用独立的初始化密码，不依赖开发者真实配置。"""
import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def bootstrap_password(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password", "test-bootstrap-password")
