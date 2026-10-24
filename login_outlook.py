"""Outlook 一次性授权脚本（device code flow）。

用法:  python login_outlook.py [account_id]
默认授权第一个 type=outlook 的账号，完成后令牌缓存到 outlook_token_cache.json。
"""
import json
import os
import sys

import msal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
    config = json.load(f)

accounts = config.get("accounts", [])

target = None
if len(sys.argv) > 1:
    target = next((a for a in accounts if a.get("id") == sys.argv[1]), None)
if target is None:
    target = next((a for a in accounts if a.get("type") == "outlook"), None)
if target is None:
    target = accounts[0] if accounts else None

if target is None:
    print("config.json 里没有任何账号")
    sys.exit(1)

client_id = target.get("client_id") or os.environ.get("AZURE_CLIENT_ID")
if not client_id:
    print("缺少 client_id：请先在 Azure 注册应用，把 client_id 填到 config.json 的该账号里")
    sys.exit(1)

authority = f"https://login.microsoftonline.com/{target.get('tenant', 'common')}"
scopes = ["https://graph.microsoft.com/Mail.Read", "offline_access"]
cache_path = os.path.join(BASE_DIR, target.get("token_cache", "outlook_token_cache.json"))

app = msal.PublicClientApplication(client_id, authority=authority,
                                  token_cache=msal.SerializableTokenCache())
if os.path.exists(cache_path):
    with open(cache_path, "r", encoding="utf-8") as f:
        app.token_cache.deserialize(f.read())

flow = app.initiate_device_flow(scopes=scopes)
print(flow["message"])
print("\n>> 用你的学校账号登录，完成授权后回到这里等待……")

result = app.acquire_token_by_device_flow(flow)
if "access_token" in result:
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(app.token_cache.serialize())
    print("登录成功！令牌已缓存到", cache_path)
else:
    print("登录失败：", result.get("error_description") or result)
    sys.exit(1)
