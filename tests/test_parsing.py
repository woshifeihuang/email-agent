"""邮件解析逻辑的冒烟测试（不需要真实凭证）。"""
import email
import os
import sys
from email.header import Header

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from providers import decode_header_str, extract_body, _extract_literal  # noqa: E402

# 中文主题 RFC2047 解码
encoded = str(Header("请于周五前提交作业", "utf-8").encode())
print("subject:", decode_header_str(encoded))
assert decode_header_str(encoded) == "请于周五前提交作业"

# 多段正文 + 附件
raw = (
    b'Content-Type: multipart/mixed; boundary="X"\r\n'
    b"\r\n"
    b'--X\r\nContent-Type: text/plain; charset="utf-8"\r\n\r\n'
    + "请提交报告".encode("utf-8")
    + b"\r\n"
    b'--X\r\nContent-Type: text/html; charset="utf-8"\r\n\r\n<p>hello</p>\r\n'
    b'--X\r\nContent-Type: application/pdf; name="report.pdf"\r\n'
    b'Content-Disposition: attachment; filename="report.pdf"\r\n\r\n%%PDF%%\r\n'
    b"--X--\r\n"
)
msg = email.message_from_bytes(raw)
body, atts = extract_body(msg)
print("body:", repr(body))
print("attachments:", atts)
assert "请提交报告" in body
assert "report.pdf" in atts

print("literal:", _extract_literal([(b"1 (BODY[TEXT] {11}", b"hello world"), b")"]).decode())

print("ALL OK")
