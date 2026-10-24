#!/usr/bin/env python3
"""邮箱 Agent 插件 —— 一键配置向导

运行:  python setup.py
作用: 引导你填写邮箱信息，自动生成 config.json。
"""
import json
import os
import sys
from getpass import getpass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

PROVIDERS = [
    {"key": "1", "id": "qq", "name": "QQ 邮箱", "host": "imap.qq.com",
     "tip": "授权码获取：网页版 mail.qq.com → 设置 → 账户 → 开启 IMAP/SMTP 服务，短信验证后得到 16 位授权码"},
    {"key": "2", "id": "163", "name": "163 邮箱", "host": "imap.163.com",
     "tip": "授权码获取：网页版 → 设置 → POP3/SMTP/IMAP → 开启 IMAP，得到授权码"},
    {"key": "3", "id": "126", "name": "126 邮箱", "host": "imap.126.com",
     "tip": "同 163：网页版设置 → 开启 IMAP，得到授权码"},
    {"key": "4", "id": "gmail", "name": "Gmail", "host": "imap.gmail.com",
     "tip": "需先开启两步验证，再生成「应用专用密码」；中国大陆需代理访问"},
    {"key": "5", "id": "outlook", "name": "Outlook / Office 365（学校/企业，若开放 IMAP）",
     "host": "outlook.office365.com",
     "tip": "多数学校已禁用 IMAP 密码登录；连不上时建议改用「转发到其它邮箱」方案（见 README）"},
    {"key": "6", "id": "custom", "name": "其它 IMAP 邮箱（自定义服务器）", "host": None,
     "tip": "需自行填写 IMAP 服务器地址（如 imap.example.com）"},
]


def read_secret(prompt):
    """终端里用 getpass 隐藏输入；非终端（如管道）回退到 input，便于测试。"""
    if sys.stdin.isatty():
        return getpass(prompt + "（输入不会显示）: ").strip()
    return input(prompt + ": ").strip()


def unique_id(base, accounts):
    idx = sum(1 for a in accounts if a["id"].startswith(base))
    return base if idx == 0 else f"{base}{idx + 1}"


def write_mcp_json():
    """生成 Claude Code 项目级配置 .mcp.json，指向本机 venv python + server.py 绝对路径。"""
    if os.name == "nt":
        python_exe = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
    else:
        python_exe = os.path.join(BASE_DIR, ".venv", "bin", "python")
    python_exe = python_exe.replace("\\", "/")
    server_path = os.path.join(BASE_DIR, "server.py").replace("\\", "/")
    cfg = {
        "mcpServers": {
            "email-mailbox": {
                "command": python_exe,
                "args": [server_path],
            }
        }
    }
    with open(os.path.join(BASE_DIR, ".mcp.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print("✅ 已生成 .mcp.json（Claude Code 项目级配置）")


def main():
    print("=" * 60)
    print("  邮箱 Agent 插件 —— 配置向导")
    print("=" * 60)
    print("本向导会引导你填写邮箱信息，自动生成 config.json。\n")

    accounts = []
    while True:
        print("\n请选择邮箱类型：")
        for p in PROVIDERS:
            print(f"  {p['key']}. {p['name']}")
        choice = input("输入序号（1-6）：").strip()
        p = next((x for x in PROVIDERS if x["key"] == choice), None)
        if not p:
            print("无效序号，请重新输入。")
            continue

        print(f"\n>>> {p['name']}")
        print(f"提示：{p['tip']}\n")

        if p["host"] is None:
            host = input("IMAP 服务器地址（如 imap.example.com）: ").strip()
            port = input("端口（默认 993）: ").strip() or "993"
        else:
            host = p["host"]
            port = "993"

        username = input("邮箱地址: ").strip()
        password = read_secret("授权码 / 密码")
        if not host or not username or not password:
            print("信息不完整，跳过该邮箱。")
            continue

        accounts.append({
            "id": unique_id(p["id"], accounts),
            "name": p["name"],
            "type": "imap",
            "host": host,
            "port": int(port),
            "use_ssl": True,
            "username": username,
            "password": password,
        })
        print(f"✅ 已添加：{username}")

        more = input("\n继续添加另一个邮箱吗？(y/n，默认 n): ").strip().lower()
        if more not in ("y", "yes"):
            break

    if not accounts:
        print("\n没有添加任何邮箱，未生成配置。")
        return

    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            old = json.load(f).get("accounts", [])
        merge = input(f"\n检测到已有配置（{len(old)} 个账号）。覆盖(o) / 合并(m)？默认覆盖: ").strip().lower()
        if merge == "m":
            accounts = old + accounts

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"accounts": accounts}, f, ensure_ascii=False, indent=2)

    write_mcp_json()

    print("\n" + "=" * 60)
    print(f"✅ 配置完成！已写入 config.json（共 {len(accounts)} 个邮箱）和 .mcp.json")
    print("下一步：用 Claude Code 打开本文件夹，对它说")
    print('  「看看邮箱有什么新邮件」即可。')
    print("=" * 60)


if __name__ == "__main__":
    main()
