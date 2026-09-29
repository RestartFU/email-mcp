# Email MCP

Local MCP server for IMAP and SMTP mailboxes. It exposes `list_accounts`, `list_folders`, `list_messages`, `read_message`, and `send_message`. Reading uses IMAP `BODY.PEEK` and does not mark messages as read. Mail content is returned to the MCP client, so only connect this server to clients you trust.

## Install

Requires Python 3.10 or newer.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
```

Set `MAIL_ADDRESS` and `MAIL_PASSWORD_FILE` in the MCP client environment. The password file should contain only the mailbox password and have permissions `0600`. Alternatively, set `MAIL_PASSWORD` directly. Optional settings are `MAIL_IMAP_HOST`, `MAIL_IMAP_PORT`, `MAIL_SMTP_HOST`, and `MAIL_SMTP_PORT`. Defaults are Mango Mail's documented hosts and ports.

Example Codex configuration in `~/.codex/config.toml`:

```toml
[mcp_servers.email]
command = "/absolute/path/email-mcp/.venv/bin/email-mcp"

[mcp_servers.email.env]
MAIL_ADDRESS = "you@example.com"
MAIL_PASSWORD_FILE = "/absolute/path/to/private/password-file"
```

Restart the MCP client after changing its configuration. The server runs over stdio and makes outbound TLS connections to the configured mail provider.

## Multiple accounts

Set `MAIL_ACCOUNTS_FILE` to a local JSON file. Each account uses its address as the selector and references a password file outside the repository. Accounts may share a password file when their mailbox credentials match.

```json
{
  "default": "contact@example.com",
  "accounts": {
    "contact@example.com": {"password_file": "/private/mail-password"},
    "catch-all@example.com": {"password_file": "/private/mail-password"}
  }
}
```

Pass `account` to any mail tool to select a mailbox, or omit it to use `default`. `list_accounts` shows available selectors. The original `MAIL_ADDRESS` and `MAIL_PASSWORD_FILE` configuration remains supported for one mailbox.

## Notes

- Message listings return at most 50 recent matches per call.
- Message bodies are capped at 100,000 characters. Attachments are listed by filename and type, but their data is not returned.
- `send_message` sends immediately. Review the recipient, subject, and body before calling it.
- No credentials or message contents are stored in this repository.

Mango Mail server settings: https://mymangomail.com/docs/articles/generic-setup
MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
