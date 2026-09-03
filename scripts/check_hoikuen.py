#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
稲沢市「認可保育園等の空き状況」ページを監視し、
最新PDFのURLが前回と変わっていたらGmailで通知するスクリプト。
"""

import os
import re
import smtplib
import sys
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://www.city.inazawa.aichi.jp/kosodate/0000004010.html"
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state", "last_pdf.txt")

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
NOTIFY_TO = os.environ.get("NOTIFY_TO", GMAIL_ADDRESS)


def fetch_latest_pdf_url() -> str:
    resp = requests.get(PAGE_URL, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    # ページ内で最初に出てくる「...aki.pdf」へのリンクが
    # 常に最新（今月分）のPDF。過去分は後方の「過去の空き状況について」に並ぶ。
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"aki\.pdf$", href):
            if href.startswith("http"):
                return href
            return "https://www.city.inazawa.aichi.jp" + href

    raise RuntimeError("PDFリンクが見つかりませんでした。ページ構成が変わった可能性があります。")


def read_last_url() -> str:
    if not os.path.exists(STATE_FILE):
        return ""
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def write_last_url(url: str) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(url + "\n")


def send_mail(new_url: str, old_url: str) -> None:
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("GMAIL_ADDRESS / GMAIL_APP_PASSWORD が未設定のため通知メールを送れません。")
        return

    subject = "【更新検知】稲沢市 保育園空き状況PDFが更新されました"
    body = (
        "稲沢市の認可保育園等空き状況PDFが更新されたようです。\n\n"
        f"新しいPDF: {new_url}\n"
        f"前回のPDF: {old_url or '(記録なし)'}\n\n"
        f"ページ: {PAGE_URL}\n"
    )
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = NOTIFY_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [NOTIFY_TO], msg.as_string())

    print("通知メールを送信しました。")


def main() -> int:
    latest_url = fetch_latest_pdf_url()
    last_url = read_last_url()

    print(f"前回: {last_url or '(なし)'}")
    print(f"最新: {latest_url}")

    if latest_url != last_url:
        print("更新を検知しました。")
        send_mail(latest_url, last_url)
        write_last_url(latest_url)
    else:
        print("更新はありません。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
