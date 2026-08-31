#!/usr/bin/env python3
"""ดึงบันทึกงานรายสัปดาห์จาก repo clio ออกมาอ่าน

สกิลนี้ **อ่านอย่างเดียว** เขียนอะไรกลับไม่ได้ และไม่มีทางไปแตะ repo งานของบริษัท
เพราะ token ที่ใช้มีสิทธิ์ Contents = Read บน repo clio ใบเดียวเท่านั้น

ใช้ของที่ Python มีมาให้ในตัวล้วน ๆ ไม่ต้องลงไลบรารีเพิ่ม

    read_log.py --list                # มีบันทึกของสัปดาห์ไหนบ้าง
    read_log.py --latest              # อ่านใบล่าสุด
    read_log.py --week 2026-W35       # อ่านใบที่ระบุ
    read_log.py --check               # สัปดาห์ที่แล้วมีบันทึกหรือยัง (ไว้ทักเตือนวันศุกร์)
    read_log.py --format              # โครงของบันทึกหน้าตายังไง
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
TIMEOUT = 30


def token() -> str:
    tok = os.environ.get("GH_CLIO_TOKEN", "").strip()
    if not tok:
        sys.exit("ยังไม่ได้ตั้ง GH_CLIO_TOKEN — ใส่ใน .env ของตัวเองแล้ว restart")
    return tok


def repo() -> str:
    return os.environ.get("CLIO_REPO", "").strip() or sys.exit(
        "ยังไม่ได้ตั้ง CLIO_REPO (รูปแบบ เจ้าของ/ชื่อrepo)")


def get(path: str, raw: bool = False):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {token()}",
            "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return body if raw else json.loads(body)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        detail = err.read().decode("utf-8", "replace")[:200]
        sys.exit(f"GitHub ตอบ {err.code}: {detail}")
    except urllib.error.URLError as err:
        sys.exit(f"ต่อ GitHub ไม่ได้: {err.reason}")


def weeks() -> list[str]:
    """คืนรายชื่อสัปดาห์ที่มีบันทึก เรียงเก่าไปใหม่ เช่น ['2026-W35', '2026-W36']"""
    found = []
    root = get(f"/repos/{repo()}/contents/") or []
    for entry in root:
        if entry.get("type") != "dir" or not entry["name"].isdigit():
            continue
        for f in get(f"/repos/{repo()}/contents/{entry['name']}") or []:
            if f.get("name", "").endswith(".md"):
                found.append(f["name"][:-3])
    return sorted(found)


def note(week: str) -> str | None:
    year = week.split("-")[0]
    return get(f"/repos/{repo()}/contents/{year}/{week}.md", raw=True)


def last_week_label() -> str:
    monday = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
    d = monday - dt.timedelta(days=7)
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--latest", action="store_true")
    g.add_argument("--week")
    g.add_argument("--check", action="store_true")
    g.add_argument("--format", action="store_true")
    a = ap.parse_args()

    if a.format:
        text = get(f"/repos/{repo()}/contents/NOTE-FORMAT.md", raw=True)
        print(text or "ไม่เจอ NOTE-FORMAT.md ใน repo")
        return 0

    if a.list:
        found = weeks()
        print("\n".join(found) if found else "ยังไม่มีบันทึกสักใบ")
        return 0

    if a.check:
        want = last_week_label()
        if want in weeks():
            print(f"มีแล้ว: {want}")
            return 0
        print(f"ยังไม่มีบันทึกของ {want}")
        return 1

    week = a.week
    if a.latest:
        found = weeks()
        if not found:
            print("ยังไม่มีบันทึกสักใบ")
            return 1
        week = found[-1]

    text = note(week)
    if text is None:
        print(f"ไม่มีบันทึกของ {week}")
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
