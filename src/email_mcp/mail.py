"""Small, synchronous mail client. Network operations run in a worker thread."""

from __future__ import annotations

import email
import imaplib
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.policy import default
from pathlib import Path


MAX_RESULTS = 50
MAX_BODY_CHARS = 100_000


@dataclass(frozen=True)
class Settings:
    address: str
    password: str
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int

    @classmethod
    def from_env(cls) -> Settings:
        address = os.environ.get("MAIL_ADDRESS", "").strip()
        password_file = os.environ.get("MAIL_PASSWORD_FILE")
        password = Path(password_file).read_text().rstrip("\r\n") if password_file else os.environ.get("MAIL_PASSWORD", "")
        if not address or not password:
            raise ValueError("MAIL_ADDRESS and MAIL_PASSWORD_FILE (or MAIL_PASSWORD) are required")
        return cls(
            address=address,
            password=password,
            imap_host=os.environ.get("MAIL_IMAP_HOST", "imap.mymangomail.com"),
            imap_port=int(os.environ.get("MAIL_IMAP_PORT", "993")),
            smtp_host=os.environ.get("MAIL_SMTP_HOST", "smtp.mymangomail.com"),
            smtp_port=int(os.environ.get("MAIL_SMTP_PORT", "465")),
        )


def _text(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (UnicodeError, ValueError):
        return value


def _body(message: Message) -> str:
    if message.is_multipart():
        plain = message.get_body(preferencelist=("plain",))
        part = plain or message.get_body(preferencelist=("html",))
        if part is None:
            return ""
        message = part
    try:
        content = message.get_content()
        return str(content)[:MAX_BODY_CHARS] if isinstance(content, str) else ""
    except (LookupError, UnicodeError, AttributeError):
        return ""


def _summary(uid: str, message: Message) -> dict[str, str]:
    return {
        "uid": uid,
        "subject": _text(message.get("Subject")),
        "from": _text(message.get("From")),
        "to": _text(message.get("To")),
        "date": message.get("Date", ""),
    }


class Mailbox:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _connect(self) -> imaplib.IMAP4_SSL:
        client = imaplib.IMAP4_SSL(
            self.settings.imap_host,
            self.settings.imap_port,
            ssl_context=ssl.create_default_context(),
            timeout=20,
        )
        try:
            client.login(self.settings.address, self.settings.password)
        except Exception:
            client.logout()
            raise
        return client

    def list_folders(self) -> list[str]:
        client = self._connect()
        try:
            status, data = client.list()
            if status != "OK":
                raise RuntimeError("Could not list folders")
            return [line.decode("utf-8", "replace") for line in data if line]
        finally:
            client.logout()

    def search(self, folder: str = "INBOX", query: str = "ALL", limit: int = 20) -> list[dict[str, str]]:
        if not 1 <= limit <= MAX_RESULTS:
            raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")
        # Keep the query narrow and predictable; arbitrary IMAP syntax can contain literals.
        allowed = {"ALL", "UNSEEN", "SEEN", "FLAGGED", "UNFLAGGED", "ANSWERED", "UNANSWERED"}
        query = query.upper()
        if query not in allowed:
            raise ValueError("query must be one of: " + ", ".join(sorted(allowed)))
        client = self._connect()
        try:
            status, _ = client.select(folder, readonly=True)
            if status != "OK":
                raise ValueError("Folder is unavailable")
            status, data = client.uid("SEARCH", None, query)
            if status != "OK":
                raise RuntimeError("Could not search mailbox")
            uids = data[0].split()[-limit:] if data and data[0] else []
            result = []
            for uid in reversed(uids):
                status, message_data = client.uid("FETCH", uid, "(BODY.PEEK[HEADER])")
                if status != "OK":
                    continue
                raw = next((part[1] for part in message_data if isinstance(part, tuple)), None)
                if raw:
                    result.append(_summary(uid.decode("ascii"), email.message_from_bytes(raw, policy=default)))
            return result
        finally:
            client.logout()

    def read(self, uid: str, folder: str = "INBOX") -> dict[str, object]:
        if not uid.isascii() or not uid.isdigit():
            raise ValueError("uid must be a numeric IMAP UID")
        client = self._connect()
        try:
            status, _ = client.select(folder, readonly=True)
            if status != "OK":
                raise ValueError("Folder is unavailable")
            status, data = client.uid("FETCH", uid, "(BODY.PEEK[])")
            if status != "OK":
                raise RuntimeError("Could not read message")
            raw = next((part[1] for part in data if isinstance(part, tuple)), None)
            if not raw:
                raise ValueError("Message not found")
            message = email.message_from_bytes(raw, policy=default)
            attachments = [
                {"filename": part.get_filename() or "", "content_type": part.get_content_type()}
                for part in message.walk()
                if part.get_content_disposition() == "attachment"
            ]
            return {**_summary(uid, message), "body": _body(message), "attachments": attachments}
        finally:
            client.logout()

    def send(self, to: list[str], subject: str, body: str, cc: list[str] | None = None) -> dict[str, object]:
        if not to:
            raise ValueError("At least one recipient is required")
        if not body:
            raise ValueError("A message body is required")
        recipients = to + (cc or [])
        if any("\r" in item or "\n" in item for item in recipients) or "\r" in subject or "\n" in subject:
            raise ValueError("Headers cannot contain newlines")
        message = EmailMessage()
        message["From"] = self.settings.address
        message["To"] = ", ".join(to)
        if cc:
            message["Cc"] = ", ".join(cc)
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP_SSL(
            self.settings.smtp_host,
            self.settings.smtp_port,
            context=ssl.create_default_context(),
            timeout=20,
        ) as client:
            client.login(self.settings.address, self.settings.password)
            client.send_message(message)
        return {"sent": True, "to": to, "cc": cc or [], "subject": subject}
