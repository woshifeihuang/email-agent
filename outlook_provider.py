"""Microsoft Graph provider for Outlook / Microsoft 365 mailboxes (OAuth).

Uses the device-code flow (done once via login_outlook.py) and a cached token.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

import msal

GRAPH = "https://graph.microsoft.com/v1.0"


def _addr(item) -> str:
    if not item:
        return ""
    ea = item.get("emailAddress") or {}
    name = ea.get("name") or ""
    address = ea.get("address") or ""
    if name and address:
        return f"{name} <{address}>"
    return name or address


def _addr_list(items) -> str:
    if not items:
        return ""
    return "; ".join(_addr(i) for i in items if i)


class OutlookProvider:
    def __init__(self, cfg: dict, base_dir: str | None = None):
        self.cfg = cfg
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.client_id = cfg.get("client_id")
        self.tenant = cfg.get("tenant", "common")
        self.authority = f"https://login.microsoftonline.com/{self.tenant}"
        self.scopes = ["https://graph.microsoft.com/Mail.Read", "offline_access"]
        cache_rel = cfg.get("token_cache", "outlook_token_cache.json")
        self.token_cache_path = os.path.join(self.base_dir, cache_rel)

    # -- auth ---------------------------------------------------------------- #

    def _app(self):
        if not self.client_id:
            raise RuntimeError("缺少 client_id：请先在 Azure 注册应用，把 client_id 填进 config.json")
        cache = msal.SerializableTokenCache()
        if os.path.exists(self.token_cache_path):
            with open(self.token_cache_path, "r", encoding="utf-8") as f:
                cache.deserialize(f.read())
        return msal.PublicClientApplication(self.client_id, authority=self.authority, token_cache=cache)

    def _token(self) -> str:
        app = self._app()
        result = None
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(self.scopes, account=accounts[0])
        if not result:
            raise RuntimeError("Outlook 尚未登录：请运行  python login_outlook.py school  完成一次授权")
        with open(self.token_cache_path, "w", encoding="utf-8") as f:
            f.write(app.token_cache.serialize())
        return result["access_token"]

    def _get(self, path: str) -> dict:
        token = self._token()
        req = urllib.request.Request(GRAPH + path, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    # -- core ---------------------------------------------------------------- #

    def _folder(self, folder: str) -> str:
        return "inbox" if folder.upper() == "INBOX" else folder

    def list_mails(self, folder: str = "INBOX", limit: int = 20, unread_only: bool = False) -> list[dict]:
        params = {"$top": str(limit),
                  "$select": "id,from,subject,receivedDateTime,isRead,bodyPreview"}
        if unread_only:
            params["$filter"] = "isRead eq false"
        qs = urllib.parse.urlencode(params)
        data = self._get(f"/me/mailFolders/{self._folder(folder)}/messages?{qs}")
        return [self._summary(m) for m in data.get("value", [])]

    def read_mail(self, mail_id: str, folder: str = "INBOX") -> dict:
        data = self._get(
            f"/me/messages/{mail_id}?$select=id,from,toRecipients,ccRecipients,"
            f"subject,receivedDateTime,body,hasAttachments"
        )
        body = data.get("body") or {}
        attachments = []
        try:
            att = self._get(f"/me/messages/{mail_id}/attachments?$select=name")
            attachments = [a.get("name", "") for a in att.get("value", [])]
        except Exception:
            pass
        return {
            "id": data.get("id", ""),
            "from": _addr(data.get("from")),
            "to": _addr_list(data.get("toRecipients")),
            "cc": _addr_list(data.get("ccRecipients")),
            "subject": data.get("subject", ""),
            "date": data.get("receivedDateTime", ""),
            "body": body.get("content", ""),
            "body_type": body.get("contentType", ""),
            "attachments": attachments,
        }

    def search_mails(self, query: str, folder: str = "INBOX", limit: int = 20, window: int = 100) -> list[dict]:
        params = {"$top": str(window),
                  "$select": "id,from,subject,receivedDateTime,isRead,bodyPreview"}
        qs = urllib.parse.urlencode(params)
        data = self._get(f"/me/mailFolders/{self._folder(folder)}/messages?{qs}")
        q = query.lower()
        matches = []
        for m in data.get("value", []):
            item = self._summary(m)
            hay = " ".join([item["subject"], item["from"], item["snippet"]]).lower()
            if q in hay:
                matches.append(item)
                if len(matches) >= limit:
                    break
        return matches

    @staticmethod
    def _summary(m: dict) -> dict:
        return {
            "id": m.get("id", ""),
            "from": _addr(m.get("from")),
            "subject": m.get("subject", ""),
            "date": m.get("receivedDateTime", ""),
            "seen": bool(m.get("isRead")),
            "snippet": (m.get("bodyPreview") or "")[:200],
        }
