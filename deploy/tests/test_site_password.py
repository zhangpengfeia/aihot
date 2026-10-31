"""验证密码配置只保存哈希、保留其他配置、拒绝损坏值。"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

DEPLOY = Path(__file__).resolve().parents[1]
with patch.object(sys, "path", [str(DEPLOY), *sys.path]):
    spec = importlib.util.spec_from_file_location(
        "set_site_password", DEPLOY / "set-site-password.py"
    )
    setter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setter)


class SitePasswordTests(unittest.TestCase):
    def test_password_goes_to_stdin_with_line_ending_and_not_command_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "site.env"
            path.write_text("SITE_USER=admin\n")
            password = "temporary-test-password"
            with (
                patch.object(
                    setter.getpass, "getpass", side_effect=[password, password]
                ),
                patch.object(setter.sys, "argv", ["set-site-password.py", str(path)]),
                patch.object(
                    setter.subprocess,
                    "run",
                    return_value=SimpleNamespace(
                        returncode=0, stdout="$2a$14$" + "A" * 53 + "\n"
                    ),
                ) as run,
            ):
                setter.main()
            self.assertEqual(run.call_args.kwargs["input"], password + "\n")
            self.assertNotIn(password, " ".join(run.call_args.args[0]))
            self.assertNotIn(password, path.read_text())

    def test_hash_format_rejects_plaintext_truncated_and_expanded_values(self):
        for value in (
            "my-password",
            "$2a$14$abc",
            "2a4abcdefgh",
            "$2a$99$" + "A" * 53,
            None,
        ):
            self.assertFalse(setter.valid_hash(value))
        self.assertTrue(setter.valid_hash("$2a$14$" + "A" * 53))

    def test_write_preserves_other_settings_quotes_hash_and_restricts_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "site.env"
            path.write_text(
                "SITE_DOMAIN=zhangff.cn\nSITE_USER=admin\nSITE_PASSWORD_HASH=wrong\n"
            )
            password_hash = "$2a$14$" + "A" * 53
            setter.write_hash(path, password_hash)
            self.assertEqual(
                path.read_text(),
                f"SITE_DOMAIN=zhangff.cn\nSITE_USER=admin\nSITE_PASSWORD_HASH='{password_hash}'\n",
            )
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            before = path.read_text()
            with self.assertRaises(ValueError):
                setter.write_hash(path, "invalid")
            self.assertEqual(path.read_text(), before)


if __name__ == "__main__":
    unittest.main()
