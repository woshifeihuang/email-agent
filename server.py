"""Email MCP server — 统一读取多个邮箱 (Outlook / Gmail / QQ邮箱 ...).

给 Claude Code 提供读取邮件的工具:
  list_accounts / list_mails / read_mail / search_mails
"""
from __future__ import annotations

import json
import os

from providers import get_provider

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # 兼容旧版 mcp 包
    from mcp.server import FastMCP  # type: ignore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

mcp = FastMCP("email-mailbox")


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {"accounts": []}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def find_account(account_id: str | None) -> dict:
    accounts = load_config().get("accounts", [])
    if not accounts:
        raise ValueError("还没有配置任何邮箱。请把 config.example.json 复制为 config.json 并填入邮箱信息。")
    if account_id is None:
        if len(accounts) == 1:
            return accounts[0]
        ids = [a.get("id") for a in accounts]
        raise ValueError(f"配置了多个邮箱，请指定 account: {ids}")
    for a in accounts:
        if a.get("id") == account_id:
            return a
    ids = [a.get("id") for a in accounts]
    raise ValueError(f"找不到邮箱 '{account_id}'，可用的有: {ids}")


def _safe(cfg, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return {"error": str(e)}


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def list_accounts() -> dict:
    """列出已配置的所有邮箱账号。"""
    accounts = load_config().get("accounts", [])
    return {
        "accounts": [
            {"id": a.get("id"), "name": a.get("name"), "type": a.get("type", "imap"),
             "email": a.get("username")}
            for a in accounts
        ]
    }


@mcp.tool()
def list_mails(account: str | None = None, folder: str = "INBOX", limit: int = 20,
               unread_only: bool = False) -> dict:
    """列出邮件（最新在前）。返回 id/发件人/主题/日期/是否已读/摘要。"""
    cfg = find_account(account)
    return _safe(cfg, lambda: {
        "account": cfg.get("id"),
        "count": 0,
        "mails": get_provider(cfg).list_mails(folder=folder, limit=limit, unread_only=unread_only),
    })


@mcp.tool()
def read_mail(account: str, mail_id: str, folder: str = "INBOX") -> dict:
    """读取一封邮件的完整正文。mail_id 来自 list_mails 返回的 id。"""
    cfg = find_account(account)
    return _safe(cfg, lambda: {"account": cfg.get("id"),
                               **get_provider(cfg).read_mail(mail_id, folder=folder)})


@mcp.tool()
def search_mails(account: str, query: str, folder: str = "INBOX", limit: int = 20) -> dict:
    """按关键词搜索邮件（主题/发件人/摘要，支持中文）。"""
    cfg = find_account(account)
    return _safe(cfg, lambda: {
        "account": cfg.get("id"),
        "query": query,
        "mails": get_provider(cfg).search_mails(query, folder=folder, limit=limit),
    })


if __name__ == "__main__":
    mcp.run()
