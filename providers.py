"""Email providers: unified read interface (IMAP for QQ/163/126; Graph for Outlook)."""
from __future__ import annotations

import email
import html
import imaplib
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime


# --------------------------------------------------------------------------- #
# Decoding helpers
# --------------------------------------------------------------------------- #

def decode_header_str(value) -> str:
    """Decode a possibly RFC2047-encoded header value into a plain string."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    parts = []
    for text, charset in decode_header(value):
        if isinstance(text, bytes):
            parts.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(text)
    return "".join(parts)


def decode_part_payload(part) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except Exception:
        return payload.decode("utf-8", errors="replace")


def _strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_body(msg) -> tuple[str, list[str]]:
    """Return (plain-text body, attachment filenames) for a parsed Message."""
    text_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = (part.get("Content-Disposition") or "").lower()
            if cdisp.startswith("attachment"):
                name = decode_header_str(part.get_filename())
                attachments.append(name or "(未命名附件)")
                continue
            if ctype == "text/plain":
                text_parts.append(decode_part_payload(part))
            elif ctype == "text/html":
                html_parts.append(decode_part_payload(part))
    else:
        ctype = msg.get_content_type()
        if ctype == "text/plain":
            text_parts.append(decode_part_payload(msg))
        elif ctype == "text/html":
            html_parts.append(decode_part_payload(msg))

    body = "\n".join(p for p in text_parts if p.strip()).strip()
    if body:
        return body, attachments
    if html_parts:
        return _strip_html("\n".join(html_parts)), attachments
    return "", attachments


def parse_date(value) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).isoformat()
    except Exception:
        return value


def _extract_literal(data):
    """Pull the literal payload bytes out of an imaplib fetch response.

    imaplib returns either a tuple (metadata, payload) or a list whose first
    element is the metadata line and whose remaining elements hold the payload.
    """
    if not data:
        return b""
    first = data[0]
    parts: list[bytes] = []
    if isinstance(first, tuple):
        if len(first) > 1:
            parts.append(first[1])
        rest = data[1:]
    else:
        rest = data[1:]
    for item in rest:
        if isinstance(item, tuple):
            if len(item) > 1:
                parts.append(item[1])
        elif isinstance(item, bytes):
            parts.append(item)
    payload = b"".join(parts)
    payload = payload.rstrip(b"\r\n")
    if payload.endswith(b")"):
        payload = payload[:-1]
    return payload


# --------------------------------------------------------------------------- #
# IMAP provider (QQ邮箱 / 163 / 126 / any IMAP mailbox)
# --------------------------------------------------------------------------- #

class ImapProvider:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def _connect(self):
        host = self.cfg["host"]
        port = int(self.cfg.get("port", 993))
        if self.cfg.get("use_ssl", True):
            conn = imaplib.IMAP4_SSL(host, port)
        else:
            conn = imaplib.IMAP4(host, port)
        conn.login(self.cfg["username"], self.cfg["password"])
        return conn

    # -- core ---------------------------------------------------------------- #

    def list_mails(self, folder: str = "INBOX", limit: int = 20, unread_only: bool = False) -> list[dict]:
        conn = self._connect()
        try:
            conn.select(folder, readonly=True)
            criteria = "(UNSEEN)" if unread_only else "ALL"
            typ, data = conn.uid("search", None, criteria)
            if typ != "OK":
                return []
            uids = data[0].split()
            unseen = self._unseen_set(conn)
            result = []
            for uid in uids[-limit:][::-1]:
                item = self._mail_summary(conn, uid, unseen)
                if item:
                    result.append(item)
            return result
        finally:
            _safe_logout(conn)

    def read_mail(self, mail_id: str, folder: str = "INBOX") -> dict:
        conn = self._connect()
        try:
            conn.select(folder, readonly=True)
            typ, data = conn.uid("fetch", mail_id, "(BODY.PEEK[])")
            if typ != "OK" or not data:
                raise ValueError(f"mail id '{mail_id}' not found")
            raw = _extract_literal(data)
            msg = email.message_from_bytes(raw)
            body, attachments = extract_body(msg)
            return {
                "id": mail_id,
                "from": decode_header_str(msg.get("From")),
                "to": decode_header_str(msg.get("To")),
                "cc": decode_header_str(msg.get("Cc")),
                "subject": decode_header_str(msg.get("Subject")),
                "date": parse_date(msg.get("Date")),
                "body": body,
                "attachments": attachments,
            }
        finally:
            _safe_logout(conn)

    def search_mails(self, query: str, folder: str = "INBOX", limit: int = 20, window: int = 100) -> list[dict]:
        """按关键词搜索（匹配主题 + 发件人，支持中文）。只抓邮件头，速度快。"""
        conn = self._connect()
        try:
            conn.select(folder, readonly=True)
            typ, data = conn.uid("search", None, "ALL")
            if typ != "OK":
                return []
            uids = data[0].split()
            unseen = self._unseen_set(conn)
            q = query.lower()
            matches = []
            for uid in uids[-window:][::-1]:
                item = self._header_summary(conn, uid, unseen)
                if not item:
                    continue
                hay = " ".join([item["subject"], item["from"]]).lower()
                if q in hay:
                    matches.append(item)
                    if len(matches) >= limit:
                        break
            return matches
        finally:
            _safe_logout(conn)

    # -- helpers ------------------------------------------------------------- #

    def _unseen_set(self, conn) -> set:
        typ, data = conn.uid("search", None, "UNSEEN")
        if typ == "OK" and data and data[0]:
            return set(data[0].split())
        return set()

    def _mail_summary(self, conn, uid, unseen: set) -> dict | None:
        try:
            typ, d = conn.uid("fetch", uid, "(BODY.PEEK[])")
            if typ != "OK" or not d:
                return None
            msg = email.message_from_bytes(_extract_literal(d))
            body, _ = extract_body(msg)
            return {
                "id": uid.decode() if isinstance(uid, bytes) else str(uid),
                "from": decode_header_str(msg.get("From")),
                "subject": decode_header_str(msg.get("Subject")),
                "date": parse_date(msg.get("Date")),
                "seen": uid not in unseen,
                "snippet": re.sub(r"\s+", " ", body)[:200],
            }
        except Exception:
            return None

    def _header_summary(self, conn, uid, unseen: set) -> dict | None:
        """只抓邮件头（快），用于搜索；不含正文摘要。"""
        try:
            typ, d = conn.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if typ != "OK" or not d:
                return None
            msg = email.message_from_bytes(_extract_literal(d))
            return {
                "id": uid.decode() if isinstance(uid, bytes) else str(uid),
                "from": decode_header_str(msg.get("From")),
                "subject": decode_header_str(msg.get("Subject")),
                "date": parse_date(msg.get("Date")),
                "seen": uid not in unseen,
                "snippet": "",
            }
        except Exception:
            return None


def _safe_logout(conn):
    try:
        conn.logout()
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Provider dispatch
# --------------------------------------------------------------------------- #

def get_provider(cfg: dict):
    t = (cfg.get("type") or "imap").lower()
    if t == "imap":
        return ImapProvider(cfg)
    if t == "outlook":
        from outlook_provider import OutlookProvider
        return OutlookProvider(cfg)
    if t == "gmail":
        raise NotImplementedError("Gmail API 通道尚未实现")
    raise ValueError(f"未知的邮箱类型: {t}")
