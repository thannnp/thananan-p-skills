#!/usr/bin/env python3
"""อ่านไฟล์ JSON ที่ collect.py สร้าง แล้วพิมพ์ออกมาแบบย่อ

ไฟล์เต็มใหญ่หลายแสนตัวอักษร อ่านทั้งก้อนแล้วเปลือง context เปล่า ๆ
ตัวนี้พิมพ์ภาพรวมก่อน แล้วค่อยเจาะดูเป็นส่วน ๆ ตามต้องการ

    outline.py recap.json                      # ภาพรวม
    outline.py recap.json --prompts horo/horoacademy-backoffice
    outline.py recap.json --pr 41              # เนื้อ PR เต็ม ๆ
    outline.py recap.json --day 2026-08-26     # เจาะรายวัน
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

MARK = {"prod": "🟢 prod", "dev": "🟡 dev", "branch": "⚪ branch"}


def mark(pr: dict) -> str:
    dep = pr.get("deploy", {})
    t = dep.get("target", "?")
    base = MARK.get(t, f"🟠 {t}")
    if t != "prod" and dep.get("in_prod"):
        base += " →prod"
    return base


def overview(d: dict) -> None:
    t = d["totals"]
    print(f"# สัปดาห์ {d['week']}  ({d['since']} ถึง {d['until']})")
    print(f"PR เปิดเอง {t['prs_authored']} (merged {t['prs_merged']}) · "
          f"ถึง prod แล้ว {t['landed_in_prod']} · ค้างที่ dev {t['waiting_on_dev']} · "
          f"รีวิวให้คนอื่น {t['prs_reviewed']} · issue ที่ยุ่งด้วย {t['issues_touched']} · "
          f"commit {t['commits']} ใน {t['repos_with_commits']} repo · "
          f"ที่พิมพ์เอง {t['prompts']} ข้อความ")

    print("\n## ปลายทาง deploy ของแต่ละ repo")
    for repo, i in d.get("deploy_by_repo", {}).items():
        ahead = len(i.get("dev_ahead") or [])
        note = f" · dev ล้ำหน้า prod {ahead} commit" if ahead else ""
        print(f"- {repo}: prod={i['prod_branch']} dev={i['dev_branch'] or '—'} "
              f"({i.get('compare_status') or 'ไม่ได้เทียบ'}){note}")

    print("\n## PR ที่เปิดเอง")
    by_repo = defaultdict(list)
    for pr in d["prs_authored"]:
        by_repo[pr["repo"]].append(pr)
    for repo, prs in sorted(by_repo.items()):
        print(f"\n### {repo}")
        for pr in sorted(prs, key=lambda p: -p["number"]):
            closes = " ".join(f"ปิด#{c['number']}" for c in pr["closes_issues"])
            print(f"- #{pr['number']} [{pr['state']}] {mark(pr)} "
                  f"{pr['base']}←{pr['head']} "
                  f"(+{pr['lines']['+']}/-{pr['lines']['-']} {pr['files_count']} ไฟล์) "
                  f"{pr['title']} {closes}".rstrip())
            why = pr["deploy"].get("why", "")
            if "squash" in why or pr["deploy"]["target"] == "branch":
                print(f"    ⚠️  {why}")

    if d.get("prs_reviewed"):
        print("\n## PR ที่ไปรีวิวให้คนอื่น")
        for pr in d["prs_reviewed"]:
            print(f"- {pr['repo']}#{pr['number']} โดย {pr['author']}: {pr['title']}")

    if d.get("issues"):
        print("\n## issue ที่ยุ่งด้วย")
        for it in d["issues"]:
            when = f" ปิด {it['closed_at'][:10]}" if it.get("closed_at") else ""
            print(f"- {it['repo']}#{it['number']} [{it['state']}]{when} {it['title']}")

    if d.get("local_commits"):
        print("\n## commit ในเครื่อง (รวมที่ยังไม่เปิด PR)")
        for r in d["local_commits"]:
            print(f"\n### {r['repo']} — {len(r['commits'])} commit")
            for c in r["commits"]:
                print(f"- {c['date']} {c['sha']} {c['subject']}")

    if d.get("prompts_by_project"):
        print("\n## ที่พิมพ์เอง — ดัชนีตามโปรเจกต์/วัน (เจาะด้วย --prompts <โปรเจกต์>)")
        for p in d["prompts_by_project"]:
            days = defaultdict(int)
            for x in p["prompts"]:
                days[(x["at"] or "")[:10]] += 1
            spread = " ".join(f"{k[5:]}×{v}" for k, v in sorted(days.items()))
            print(f"- {p['project']} ({p['count']}) {spread}")


def show_prompts(d: dict, needle: str) -> None:
    for p in d["prompts_by_project"]:
        if needle.lower() not in p["project"].lower():
            continue
        print(f"\n## {p['project']} — {p['count']} ข้อความ")
        day = None
        for x in p["prompts"]:
            if (x["at"] or "")[:10] != day:
                day = (x["at"] or "")[:10]
                print(f"\n### {day}")
            branch = f" [{x['branch']}]" if x.get("branch") else ""
            print(f"- {(x['at'] or '')[11:16]}{branch} {x['text']}")


def show_pr(d: dict, number: int) -> None:
    for pr in d["prs_authored"] + d.get("prs_reviewed", []):
        if pr["number"] != number:
            continue
        print(f"# {pr['repo']}#{pr['number']} {pr['title']}")
        print(f"{pr['url']} · {pr['state']} · {pr['base']}←{pr['head']} · "
              f"{pr['deploy']['target']} · ถึง prod: {pr['deploy']['in_prod']} "
              f"({pr['deploy']['why']})")
        print("\n## ไฟล์")
        for f in pr["files"]:
            print(f"- {f['path']} +{f['+']}/-{f['-']}")
        print("\n## เนื้อ PR\n" + (pr["body"] or "(ว่าง)"))


def show_day(d: dict, day: str) -> None:
    print(f"# {day}")
    print("\n## PR")
    for pr in d["prs_authored"]:
        if (pr.get("merged_at") or pr.get("created_at") or "")[:10] == day:
            print(f"- {pr['repo']}#{pr['number']} {mark(pr)} {pr['title']}")
    print("\n## commit")
    for r in d.get("local_commits", []):
        for c in r["commits"]:
            if c["date"] == day:
                print(f"- {r['repo']} {c['sha']} {c['subject']}")
    print("\n## ที่พิมพ์เอง")
    for p in d.get("prompts_by_project", []):
        for x in p["prompts"]:
            if (x["at"] or "")[:10] == day:
                print(f"- [{p['project']}] {(x['at'] or '')[11:16]} {x['text']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--prompts", help="ชื่อโปรเจกต์ (บางส่วนก็ได้)")
    ap.add_argument("--pr", type=int)
    ap.add_argument("--day")
    a = ap.parse_args()
    d = json.load(open(a.file))
    if a.prompts:
        show_prompts(d, a.prompts)
    elif a.pr:
        show_pr(d, a.pr)
    elif a.day:
        show_day(d, a.day)
    else:
        overview(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
