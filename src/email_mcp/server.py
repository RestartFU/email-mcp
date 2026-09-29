"""MCP entry point for a single configured mailbox."""

from __future__ import annotations

import asyncio

from mcp.server import MCPServer

from .mail import Mailbox, Settings


server = MCPServer("email-mcp")


def mailbox() -> Mailbox:
    return Mailbox(Settings.from_env())


@server.tool()
async def list_folders() -> list[str]:
    """List folders in the configured email mailbox."""
    return await asyncio.to_thread(mailbox().list_folders)


@server.tool()
async def list_messages(folder: str = "INBOX", query: str = "ALL", limit: int = 20) -> list[dict[str, str]]:
    """List recent messages without marking them read. Query: ALL, UNSEEN, SEEN, FLAGGED, UNFLAGGED, ANSWERED, or UNANSWERED."""
    return await asyncio.to_thread(mailbox().search, folder, query, limit)


@server.tool()
async def read_message(uid: str, folder: str = "INBOX") -> dict[str, object]:
    """Read a message by its IMAP UID without changing its read status."""
    return await asyncio.to_thread(mailbox().read, uid, folder)


@server.tool()
async def send_message(to: list[str], subject: str, body: str, cc: list[str] | None = None) -> dict[str, object]:
    """Send a plain text email from the configured account."""
    return await asyncio.to_thread(mailbox().send, to, subject, body, cc)


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
