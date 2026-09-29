import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from email_mcp.mail import Settings


class AccountSettingsTest(unittest.TestCase):
    def test_selects_configured_mailbox(self):
        with tempfile.TemporaryDirectory() as directory:
            password_file = Path(directory) / "password"
            password_file.write_text("shared-secret\n")
            accounts_file = Path(directory) / "accounts.json"
            accounts_file.write_text(json.dumps({
                "default": "first@example.com",
                "accounts": {
                    "first@example.com": {"password_file": str(password_file)},
                    "second@example.com": {"password_file": str(password_file)},
                },
            }))
            with patch.dict("os.environ", {"MAIL_ACCOUNTS_FILE": str(accounts_file)}):
                self.assertEqual(Settings.accounts(), ("first@example.com", ["first@example.com", "second@example.com"]))
                self.assertEqual(Settings.from_env().address, "first@example.com")
                second = Settings.from_env("second@example.com")
                self.assertEqual(second.address, "second@example.com")
                self.assertEqual(second.password, "shared-secret")
                with self.assertRaisesRegex(ValueError, "Unknown email account"):
                    Settings.from_env("unknown@example.com")

    def test_single_mailbox_configuration_still_works(self):
        with patch.dict("os.environ", {"MAIL_ADDRESS": "first@example.com", "MAIL_PASSWORD": "secret"}, clear=True):
            self.assertEqual(Settings.accounts(), ("first@example.com", ["first@example.com"]))
            self.assertEqual(Settings.from_env().password, "secret")


if __name__ == "__main__":
    unittest.main()
