"""连通性测试：登录某个账号并列出几封邮件。

用法:  python tests/test_connect.py [account_id]
不传 account_id 时，测试第一个配置的账号。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from providers import get_provider  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
    cfg = json.load(f)

account_id = sys.argv[1] if len(sys.argv) > 1 else None
accounts = cfg["accounts"]
target = next((a for a in accounts if a["id"] == account_id), accounts[0])

print(f"连接 {target['name']} ({target['username']}) ...")
p = get_provider(target)
mails = p.list_mails(limit=5)
print(f"成功！最近 {len(mails)} 封：")
for m in mails:
    print(f"- [{m['id']}] {'未读' if not m['seen'] else '已读'} {m['date']} | {m['from']} | {m['subject'][:50]}")
