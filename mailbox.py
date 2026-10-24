#!/usr/bin/env python3
"""邮箱阅读器（独立命令行版）—— 不需要 Claude Code。

用法：
  python mailbox.py                列出最近邮件（自动标记"⚠️需要处理"）
  python mailbox.py list 20        列出最近 20 封
  python mailbox.py unread         只看未读邮件
  python mailbox.py read <ID>      读某封邮件的完整正文
  python mailbox.py search <关键词>  按主题 / 发件人搜索

前提：先运行过一次 setup.py 生成 config.json。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from providers import get_provider  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# 判断"这封邮件可能需要你处理"的关键词（中英文）
ACTION_KEYWORDS = [
    # 英文
    "deadline", "due", "submit", "renew", "renewal", "required", "reminder",
    "payment", "invoice", "expir", "action required", "urgent", "overdue",
    # 中文
    "截止", "提交", "续签", "缴费", "付款", "提醒", "更新", "上传", "完成",
    "注册", "选课", "签证", "尽快", "请在", "请于",
]


def load_account():
    if not os.path.exists(CONFIG_PATH):
        print("❌ 未找到 config.json，请先运行 setup.py 配置邮箱。")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        accounts = json.load(f).get("accounts", [])
    if not accounts:
        print("❌ config.json 里还没有邮箱，请先运行 setup.py。")
        sys.exit(1)
    return accounts[0]


def needs_action(subject, body):
    text = f"{subject} {body}".lower()
    return any(kw in text for kw in ACTION_KEYWORDS)


def short_date(date):
    return date[:10] if date else "?"


def print_list(mails, title):
    print(f"\n{title}（共 {len(mails)} 封）")
    print("-" * 60)
    if not mails:
        print("（无）")
        return
    for m in mails:
        tag = "未读" if not m["seen"] else "已读"
        flag = "  ⚠️需要处理" if needs_action(m["subject"], m.get("snippet", "")) else ""
        print(f"[{tag}]{flag}  {short_date(m['date'])}  (ID: {m['id']})")
        print(f"    来自: {m['from']}")
        print(f"    主题: {m['subject']}")
        if m.get("snippet"):
            print(f"    摘要: {m['snippet'][:120]}")


def cmd_list(limit=10, unread_only=False):
    p = get_provider(load_account())
    mails = p.list_mails(limit=limit, unread_only=unread_only)
    print_list(mails, "未读邮件" if unread_only else "最近邮件")


def cmd_read(mail_id):
    p = get_provider(load_account())
    m = p.read_mail(mail_id)
    print(f"\n主题: {m['subject']}")
    print(f"来自: {m['from']}")
    print(f"时间: {m['date']}")
    if m.get("attachments"):
        print(f"附件: {', '.join(m['attachments'])}")
    print("-" * 60)
    print(m["body"] if m["body"].strip() else "（无正文）")


def cmd_search(query, limit=20):
    p = get_provider(load_account())
    mails = p.search_mails(query, limit=limit)
    print_list(mails, f"搜索「{query}」结果")


def main():
    args = sys.argv[1:]
    if not args:
        cmd_list(limit=10)
        print("\n用法: python mailbox.py [list 数量 | unread | read 邮件ID | search 关键词]")
        return
    cmd = args[0].lower()
    if cmd == "list":
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        cmd_list(limit=n)
    elif cmd == "unread":
        cmd_list(limit=20, unread_only=True)
    elif cmd == "read":
        if len(args) < 2:
            print("用法: python mailbox.py read <邮件ID>")
            return
        cmd_read(args[1])
    elif cmd == "search":
        if len(args) < 2:
            print("用法: python mailbox.py search <关键词>")
            return
        cmd_search(args[1])
    else:
        print(f"未知命令: {cmd}")
        print("用法: python mailbox.py [list 数量 | unread | read 邮件ID | search 关键词]")


if __name__ == "__main__":
    main()
