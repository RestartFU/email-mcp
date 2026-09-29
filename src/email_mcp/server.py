"""MCP entry point for configured mailboxes."""

from __future__ import annotations

import asyncio

from mcp.server import MCPServer

from .mail import Mailbox, Settings


server = MCPServer("email-mcp")


def mailbox(account: str | None = None) -> Mailbox:
    return Mailbox(Settings.from_env(account))


@server.tool()
async def list_accounts() -> dict[str, object]:
    """List configured email addresses and the default account."""
    default, accounts = Settings.accounts()
    return {"default": default, "accounts": accounts}


@server.tool()
async def list_folders(account: str | None = None) -> list[str]:
    """List folders in an email mailbox. Omit account to use the default."""
    return await asyncio.to_thread(mailbox(account).list_folders)


@server.tool()
async def list_messages(folder: str = "INBOX", query: str = "ALL", limit: int = 20, account: str | None = None) -> list[dict[str, str]]:
    """List recent messages without marking them read. Query: ALL, UNSEEN, SEEN, FLAGGED, UNFLAGGED, ANSWERED, or UNANSWERED."""
    return await asyncio.to_thread(mailbox(account).search, folder, query, limit)


@server.tool()
async def read_message(uid: str, folder: str = "INBOX", account: str | None = None) -> dict[str, object]:
    """Read a message by its IMAP UID without changing its read status."""
    return await asyncio.to_thread(mailbox(account).read, uid, folder)


@server.tool()
async def send_message(to: list[str], subject: str, body: str, cc: list[str] | None = None, account: str | None = None) -> dict[str, object]:
    """Send a plain text email from the configured account."""
    return await asyncio.to_thread(mailbox(account).send, to, subject, body, cc)


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
