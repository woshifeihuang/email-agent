# 邮箱 Agent 插件（Email MCP）

让 **Claude Code** 自动登录并读取你的邮箱，把邮件里的**要求 / 待办事项**总结反馈给你。挂上插件后，说一句「看看邮箱有什么新邮件」，它就会去读邮件、再告诉你需要做什么。

---

## 快速开始（三步，给新使用者）

```powershell
# 第 1 步：一键安装（Windows 双击 install.bat 即可，等价于下面两行）
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 第 2 步：运行配置向导，照提示填写你的邮箱
.venv\Scripts\python setup.py

# 第 3 步：用 Claude Code 打开本文件夹，对它说「看看邮箱」
```

> 不用手动改 config.json —— 向导会自动生成。手动填写的详细说明见下文各章节。

---

## 一、当前状态

| 邮箱 | 方案 | 状态 |
|---|---|---|
| QQ 邮箱 | IMAP（授权码） | ✅ 已跑通 |
| 学校 Outlook | 转发到 QQ 邮箱 | ✅ 已跑通（已验证） |
| Outlook OAuth 直连 | Microsoft Graph | ⏸ 备用（代码就绪，未启用） |
| Gmail | IMAP / API | ⏳ 未开始 |

> **为什么学校 Outlook 用「转发」而不是直连**：UCSI 这类学校邮箱已禁用密码登录（报 `Basic authentication is disabled`），且禁止学生自己注册 Azure 应用。因此让学校邮箱**自动转发到 QQ**，agent 只读 QQ 就能同时掌握两个邮箱。而且学校的重要通知（签证、选课等）本来就会直接发到登记的联系邮箱（QQ）。

---

## 二、目录结构

```
Agent邮箱/
├── server.py            # MCP 服务器入口（定义 4 个工具）
├── providers.py         # IMAP 通道（QQ/163/126/通用 IMAP）
├── outlook_provider.py  # Outlook OAuth 通道（备用，需 Azure client_id）
├── login_outlook.py     # Outlook 授权脚本（备用）
├── setup.py             # 一键配置向导（引导填写邮箱 → 生成 config.json）
├── install.bat          # Windows 一键安装脚本
├── config.json          # 你的邮箱配置（含凭证，已 gitignore）
├── config.example.json  # 配置模板
├── requirements.txt     # 依赖
├── .mcp.json            # Claude Code 项目级配置（setup.py 自动生成，已 gitignore）
└── tests/
    ├── test_connect.py  # 连通性测试
    └── test_parsing.py  # 解析逻辑冒烟测试
```

---

## 三、安装

**最简单：Windows 双击 `install.bat`**，它会自动建虚拟环境、装依赖、然后启动配置向导。

手动等价于：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python setup.py      # 引导填写邮箱 → 生成 config.json
```

依赖：`mcp`（1.x）、`msal`（仅 Outlook OAuth 备用通道用到）。

---

## 四、配置邮箱

把 `config.example.json` 复制为 `config.json`，按需填写。

### 1. QQ 邮箱（推荐先配这个）

1. 网页版 https://mail.qq.com 登录 → **设置 → 账户**
2. 开启 **「IMAP/SMTP 服务」**，短信验证后得到**一串 16 位授权码**（字母+数字，只显示一次）
3. 填入 `config.json`：

```json
{
  "id": "qq",
  "name": "QQ邮箱",
  "type": "imap",
  "host": "imap.qq.com",
  "port": 993,
  "use_ssl": true,
  "username": "你的QQ号@qq.com",
  "password": "那串16位授权码"
}
```

> ⚠️ 填**授权码**，不是 QQ 密码。

### 2. 学校 Outlook（推荐：转发方案，无需改 config.json）

1. 打开 https://outlook.office.com 用学校账号登录
2. 右上角 **齿轮（设置）→ 邮件 → 转发**
3. 打开 **「启用转发」**，填入 QQ 邮箱地址，**保存**
4. （可选）勾选「保留副本」，学校邮箱里也留一份

之后学校邮件会自动转到 QQ，agent 读 QQ 即覆盖学校邮箱，**不需要在 config.json 里配学校账号**。

### 3. 学校 Outlook（备用：OAuth 直连）

若将来需要**直连**学校邮箱（不经过转发），用**个人**微软账号注册 Azure 应用：

1. 打开 https://portal.azure.com 用个人微软账号登录（学校账号注册会被拦）
2. 搜索 **App registrations → New registration**，名称随便填，**Supported account types** 选「Accounts in any organizational directory and personal Microsoft accounts」，Redirect URI 留空
3. 复制 **Application (client) ID**
4. **API permissions → Add a permission → Microsoft Graph → Delegated permissions** → 勾选 **Mail.Read** → Add
5. **Authentication → Advanced settings** → 打开 **Allow public client flows** → Save
6. 在 `config.json` 加一个 `type: "outlook"` 的账号，填上 client_id，然后：

```powershell
.venv\Scripts\python login_outlook.py
```

脚本会打印网址+代码，用学校账号登录点「同意」，令牌自动缓存。

### 4. 通用 IMAP 参数速查

| 邮箱 | host | port |
|---|---|---|
| QQ 邮箱 | imap.qq.com | 993 |
| 163 | imap.163.com | 993 |
| 126 | imap.126.com | 993 |
| Outlook / Office 365（若学校开放 IMAP） | outlook.office365.com | 993 |
| Gmail（应用专用密码） | imap.gmail.com | 993 |

---

## 五、加载到 Claude Code

`setup.py` 已自动生成 `.mcp.json`（指向本机 venv python 和 server.py 的绝对路径），因此：

- **方式一（项目级，推荐）**：在本目录启动 Claude Code，自动读取 `.mcp.json` 加载，无需手动配置。
- **方式二（全局，多项目共用）**：

```powershell
claude mcp add email-mailbox -- .venv\Scripts\python "<你的项目路径>\server.py"
```

> 把 `<你的项目路径>` 换成本文件夹的实际路径（即 `setup.py` 所在文件夹）。

---

## 六、使用

对 Claude 说下面这些话即可：

- 「看看邮箱有什么新邮件」
- 「有哪些未读邮件？」
- 「读一下 Student Pass 那封，总结要做什么」
- 「搜索主题/发件人包含 xxx 的邮件」

---

## 七、提供的工具

| 工具 | 作用 |
|---|---|
| `list_accounts` | 列出已配置的所有邮箱 |
| `list_mails` | 列邮件（可选账号、只看未读、限制数量），含正文摘要 |
| `read_mail` | 读某封邮件的完整正文 + 附件名 |
| `search_mails` | 按关键词搜索主题+发件人（快，支持中文） |

---

## 八、测试

```powershell
# 连通性测试（登录某账号并列出几封邮件）
.venv\Scripts\python tests\test_connect.py qq

# 解析逻辑冒烟测试（无需真实凭证）
.venv\Scripts\python tests\test_parsing.py
```

---

## 九、安全提示

- `config.json` 含授权码明文、`outlook_token_cache.json` 含 OAuth 令牌，均已 gitignore，**请勿上传公开仓库**。
- 授权码 / 密码泄露时，到对应邮箱设置里**重置授权码 / 密码**。

---

## 十、常见问题

| 现象 | 原因 / 处理 |
|---|---|
| `Basic authentication is disabled` | 学校/企业禁了 IMAP 密码登录，改用转发或 OAuth |
| QQ 报 `AUTHENTICATIONFAILED` | 用了 QQ 密码而不是授权码；或 IMAP 服务未开启 |
| Azure 报「你没有访问权限」 | 学校账号被限制注册应用，换**个人**微软账号登录 |
| 学校邮箱收不到外部邮件 | 学校可能只收校内发件人；重要通知通常直接发 QQ |
| 邮件正文乱码 | 已处理 RFC2047 / base64 / quoted-printable，如仍乱码请反馈具体邮件 |
