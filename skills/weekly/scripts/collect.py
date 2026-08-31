#!/usr/bin/env python3
"""รวบรวมกิจกรรมของสัปดาห์ออกมาเป็น JSON ก้อนเดียว

แหล่งข้อมูล 4 ทาง
  1. PR ที่เปิดเอง (พร้อมเนื้อ PR, ไฟล์ที่แตะ, issue ที่ปิด)
  2. PR ที่ไปรีวิวให้คนอื่น
  3. commit ในเครื่อง — จับงานที่ยังไม่ได้เปิด PR
  4. สิ่งที่เจ้าของ "พิมพ์" ใน Claude Code — จับงานที่ไม่ทิ้งร่องรอยใน git
     (ไล่ debug prod, แก้สิทธิ์ DB, ตามงานคนอื่น) เอาเฉพาะข้อความที่พิมพ์เอง
     ไม่เอาสิ่งที่ผู้ช่วยตอบกลับ

ใช้ gh cli ที่ล็อกอินอยู่แล้ว ไม่ต้องตั้ง token เพิ่ม

    python3 collect.py                     # สัปดาห์นี้ (จันทร์ที่ผ่านมา -> วันนี้)
    python3 collect.py --last              # สัปดาห์ที่แล้ว จันทร์ถึงอาทิตย์
    python3 collect.py --week 2026-W35
    python3 collect.py --since 2026-08-01 --until 2026-08-15
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")

def _who() -> tuple[str, tuple[str, ...]]:
    """ตัวเจ้าของคือใคร — ถามจาก gh กับ git config ไม่ hardcode ไว้ในสกิล

    ตั้งทับได้ด้วย WEEKLY_GH_LOGIN และ WEEKLY_AUTHOR_MATCH (คั่นด้วยจุลภาค)
    """
    login = os.environ.get("WEEKLY_GH_LOGIN") or subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True, text=True).stdout.strip()
    extra = os.environ.get("WEEKLY_AUTHOR_MATCH", "")
    match = [m.strip().lower() for m in extra.split(",") if m.strip()]
    if not match:
        email = subprocess.run(["git", "config", "--global", "user.email"],
                               capture_output=True, text=True).stdout.strip()
        match = [x for x in (login.lower(), email.split("@")[0].lower()) if x]
    return login, tuple(match)


GH_LOGIN, AUTHOR_MATCH = _who()

# โฟลเดอร์ที่ไปหา git repo
REPO_ROOTS = (HOME, os.path.join(HOME, "horo"), os.path.join(HOME, "horo", "tiktok-minigame"))

SKIP_DIRS = (".nvm", "node_modules", "Library", ".vscode", ".cache")

PROMPT_MAX = 500        # ตัดข้อความที่พิมพ์ยาว ๆ
BODY_MAX = 2000         # ตัดเนื้อ PR ยาว ๆ
FILES_MAX = 40


def run(cmd: list[str], check: bool = False) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        if check:
            raise RuntimeError(f"{' '.join(cmd[:3])}... ล้ม: {p.stderr[:300]}")
        return ""
    return p.stdout


def gh_json(args: list[str]) -> list | dict:
    out = run(["gh", *args])
    if not out.strip():
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return []


# ---------- ช่วงเวลา ----------

def resolve_range(a) -> tuple[dt.date, dt.date, str]:
    today = dt.date.today()
    if a.since:
        since = dt.date.fromisoformat(a.since)
        until = dt.date.fromisoformat(a.until) if a.until else today
    elif a.week:
        year, wk = a.week.upper().split("-W")
        since = dt.date.fromisocalendar(int(year), int(wk), 1)
        until = since + dt.timedelta(days=6)
    elif a.last:
        monday = today - dt.timedelta(days=today.weekday())
        since = monday - dt.timedelta(days=7)
        until = since + dt.timedelta(days=6)
    else:
        since = today - dt.timedelta(days=today.weekday())
        until = today
    iso = since.isocalendar()
    return since, until, f"{iso.year}-W{iso.week:02d}"


# ---------- 1+2. GitHub ----------

def collect_prs(since: dt.date, until: dt.date, flag: str) -> list[dict]:
    rng = f"{since.isoformat()}..{until.isoformat()}"
    found = gh_json([
        "search", "prs", flag, GH_LOGIN, "--updated", rng, "--limit", "60",
        "--json", "url,title,repository,state,createdAt,updatedAt,number",
    ])
    out = []
    for pr in found if isinstance(found, list) else []:
        detail = gh_json([
            "pr", "view", pr["url"], "--json",
            "title,body,state,mergedAt,createdAt,closedAt,additions,deletions,"
            "files,labels,baseRefName,headRefName,closingIssuesReferences,author,mergeCommit",
        ])
        if not isinstance(detail, dict):
            detail = {}
        # PR ของคนอื่นที่เราไปรีวิว ให้บอกว่าเจ้าของเป็นใคร
        author = (detail.get("author") or {}).get("login", "")
        files = [
            {"path": f.get("path"), "+": f.get("additions"), "-": f.get("deletions")}
            for f in (detail.get("files") or [])[:FILES_MAX]
        ]
        body = (detail.get("body") or "").strip()
        out.append({
            "repo": pr["repository"]["nameWithOwner"],
            "number": pr["number"],
            "title": detail.get("title") or pr["title"],
            "url": pr["url"],
            "author": author,
            "state": (detail.get("state") or pr["state"]).lower(),
            "merged_at": detail.get("mergedAt"),
            "created_at": detail.get("createdAt") or pr.get("createdAt"),
            "merge_sha": (detail.get("mergeCommit") or {}).get("oid", ""),
            "base": detail.get("baseRefName"),
            "head": detail.get("headRefName"),
            "lines": {"+": detail.get("additions"), "-": detail.get("deletions")},
            "files_count": len(detail.get("files") or []),
            "files": files,
            "labels": [l.get("name") for l in (detail.get("labels") or [])],
            "closes_issues": [
                {"number": i.get("number"), "title": i.get("title"), "url": i.get("url")}
                for i in (detail.get("closingIssuesReferences") or [])
            ],
            "body": body[:BODY_MAX] + ("\n…(ตัด)" if len(body) > BODY_MAX else ""),
        })
    return out


def collect_issues(since: dt.date, until: dt.date) -> list[dict]:
    rng = f"{since.isoformat()}..{until.isoformat()}"
    found = gh_json([
        "search", "issues", "--involves", GH_LOGIN, "--updated", rng,
        "--limit", "40", "--json",
        "url,title,repository,state,number,createdAt,updatedAt,closedAt,labels,body",
    ])
    out = []
    for it in found if isinstance(found, list) else []:
        body = (it.get("body") or "").strip()
        out.append({
            "repo": it["repository"]["nameWithOwner"],
            "number": it["number"],
            "title": it["title"],
            "url": it["url"],
            "state": it.get("state"),
            "closed_at": it.get("closedAt"),
            "updated_at": it.get("updatedAt"),
            "labels": [l.get("name") for l in (it.get("labels") or [])],
            "body": body[:BODY_MAX] + ("\n…(ตัด)" if len(body) > BODY_MAX else ""),
        })
    return out


# ---------- 3. commit ในเครื่อง ----------

def find_repos() -> list[str]:
    seen = []
    for root in REPO_ROOTS:
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            if entry in SKIP_DIRS or entry.startswith("."):
                continue
            path = os.path.join(root, entry)
            if os.path.isdir(os.path.join(path, ".git")) and path not in seen:
                seen.append(path)
    return seen


def collect_commits(since: dt.date, until: dt.date) -> list[dict]:
    end = (until + dt.timedelta(days=1)).isoformat()
    out = []
    for repo in find_repos():
        raw = run([
            "git", "-C", repo, "log", "--all", "--no-merges",
            f"--since={since.isoformat()}", f"--until={end}",
            "--date=short", "--pretty=format:%H%x1f%ad%x1f%ae%x1f%s%x1f%D", "--shortstat",
        ])
        if not raw.strip():
            continue
        commits = []
        current = None
        for line in raw.splitlines():
            if "\x1f" in line:
                sha, date, email, subject, refs = (line.split("\x1f") + [""] * 5)[:5]
                if not any(m in email.lower() for m in AUTHOR_MATCH):
                    current = None
                    continue
                current = {"sha": sha[:8], "date": date, "subject": subject,
                           "refs": refs, "stat": ""}
                commits.append(current)
            elif current is not None and line.strip():
                current["stat"] = line.strip()
        if commits:
            out.append({"repo": os.path.relpath(repo, HOME), "commits": commits})
    return out


# ---------- 4. สิ่งที่เจ้าของพิมพ์ ----------

NOISE_PREFIX = ("<command-name>", "<local-command-stdout>", "<system-reminder>",
                "Caveat:", "<command-message>", "[Request interrupted",
                "<user-prompt-submit-hook>", "API Error")


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(parts)
    return ""


def collect_prompts(since: dt.date, until: dt.date) -> list[dict]:
    lo, hi = since.isoformat(), (until + dt.timedelta(days=1)).isoformat()
    by_project: dict[str, list] = {}
    for path in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")):
        if dt.date.fromtimestamp(os.path.getmtime(path)) < since:
            continue
        try:
            fh = open(path, errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"type":"user"' not in line and '"type": "user"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("type") != "user" or d.get("isSidechain"):
                    continue
                src = d.get("promptSource")
                if src == "system":
                    continue
                ts = (d.get("timestamp") or "")[:10]
                if not (lo <= ts < hi):
                    continue
                txt = text_of(d.get("message", {}).get("content")).strip()
                if not txt or txt.startswith(NOISE_PREFIX) or len(txt) < 4:
                    continue
                if src is None and not txt[:1].isalnum() and not ord(txt[:1]) > 3000:
                    continue
                cwd = d.get("cwd") or "?"
                key = os.path.relpath(cwd, HOME) if cwd.startswith(HOME) else cwd
                by_project.setdefault(key, []).append({
                    "at": d.get("timestamp"),
                    "branch": d.get("gitBranch") or "",
                    "text": txt[:PROMPT_MAX] + ("…" if len(txt) > PROMPT_MAX else ""),
                })
    out = []
    for project, items in by_project.items():
        items.sort(key=lambda x: x["at"] or "")
        out.append({"project": project, "count": len(items), "prompts": items})
    out.sort(key=lambda x: -x["count"])
    return out



# ---------- งานนี้ไปถึง dev หรือ prod แล้ว ----------

DEV_BRANCHES = ("dev", "development", "staging", "backoffice-dev")
ENV_HINT = {"prod": ("prod", "production"), "dev": ("dev", "development", "staging")}


def normalize_title(t: str) -> str:
    t = re.sub(r"\(#\d+\)", "", t or "").strip().lower()
    return re.sub(r"\s+", " ", t)


def repo_branches(repo: str, bases: tuple[str, ...] = ()) -> dict:
    """หา branch ปลายทางของ prod กับ dev แล้วดึงประวัติ prod มาไว้เทียบ

    เทียบด้วย sha ก่อน ถ้าไม่เจอค่อยเทียบด้วยชื่อหัวข้อ เพราะบาง repo
    (minigame) ประวัติ main กับ dev แยกกันถาวร ต้อง cherry-pick sha จึงไม่ตรง

    ห้ามเชื่อ default_branch ว่าคือ prod — minigame-service ตั้ง default เป็น dev
    ทำให้งานที่เพิ่งเข้า dev ถูกนับว่าขึ้น prod แล้วทั้งที่ยังไม่ขึ้น
    """
    names = [n for n in run(
        ["gh", "api", f"repos/{repo}/branches", "--paginate", "-q", ".[].name"]).split() if n]
    if not names:
        meta = gh_json(["api", f"repos/{repo}"])
        names = [meta.get("default_branch", "main")] if isinstance(meta, dict) else ["main"]
    prod = next((b for b in ("main", "master", "prod", "production") if b in names), names[0])
    # dev คืออันที่ PR ของสัปดาห์นี้ยิงไปจริง ถ้าไม่มีค่อยเดาจากรายชื่อ
    dev = next((b for b in bases if b != prod and b in DEV_BRANCHES and b in names), "")
    if not dev:
        dev = next((b for b in DEV_BRANCHES if b in names), "")

    commits = gh_json(["api", f"repos/{repo}/commits?sha={prod}&per_page=100",
                       "-q", "[.[] | {sha: .sha, msg: .commit.message}]"])
    shas, titles = set(), set()
    for c in commits if isinstance(commits, list) else []:
        shas.add(c.get("sha", ""))
        first = (c.get("msg") or "").splitlines()[0] if c.get("msg") else ""
        titles.add(normalize_title(first))
        m = re.search(r"#(\d+)", first)
        if m:
            titles.add("#" + m.group(1))

    ahead = []
    if dev:
        cmp_ = gh_json(["api", f"repos/{repo}/compare/{prod}...{dev}"])
        if isinstance(cmp_, dict):
            ahead = [{"sha": c.get("sha", "")[:8],
                      "subject": (c.get("commit", {}).get("message") or "").splitlines()[0]}
                     for c in (cmp_.get("commits") or [])][-40:]
            status = cmp_.get("status", "")
        else:
            status = ""
    else:
        status = ""
    return {"prod_branch": prod, "dev_branch": dev, "compare_status": status,
            "dev_ahead": ahead, "_shas": shas, "_titles": titles}


def envs_from_files(files: list[dict]) -> list[str]:
    """repo อย่าง iac-gitops แตะ dev หรือ prod ดูจาก path ของไฟล์"""
    found = set()
    for f in files:
        parts = {s.lower() for s in (f.get("path") or "").split("/")}
        for env, hints in ENV_HINT.items():
            if parts & set(hints):
                found.add(env)
    return sorted(found)


def annotate_deploy(prs: list[dict]) -> dict:
    cache: dict[str, dict] = {}
    for pr in prs:
        repo = pr["repo"]
        if repo not in cache:
            bases = tuple(x.get("base") or "" for x in prs if x["repo"] == repo)
            cache[repo] = repo_branches(repo, bases)
        info = cache[repo]
        base = pr.get("base") or ""
        envs = envs_from_files(pr.get("files") or [])

        sha_seen = bool(pr.get("merge_sha")) and pr["merge_sha"] in info["_shas"]

        if base == info["prod_branch"]:
            target, in_prod = "prod", pr["state"] == "merged"
            how = "merged เข้า %s ตรง ๆ" % info["prod_branch"]
            if in_prod and pr.get("merge_sha") and not sha_seen:
                how += " — แต่ไม่เจอ sha ใน 100 commit ล่าสุดของ prod ต้องเช็คว่าโดน squash กลืนไหม"
        elif base in DEV_BRANCHES:
            target = "dev"
            in_prod, how = False, "ยังค้างที่ dev"
            if pr["state"] == "merged":
                if pr.get("merge_sha") and pr["merge_sha"] in info["_shas"]:
                    in_prod, how = True, "sha ของ PR อยู่ใน main แล้ว"
                elif normalize_title(pr["title"]) in info["_titles"]:
                    in_prod, how = True, "หัวข้อเดียวกันโผล่ใน main (น่าจะ cherry-pick)"
        else:
            target = "branch"
            in_prod, how = False, f"ยังอยู่บนสาขา {base} ยังไม่เข้า dev"

        # gitops: main คือที่เก็บ config ของทั้งสอง env ต้องดูจาก path ว่าแตะ env ไหน
        if envs and repo.endswith("iac-gitops"):
            target = "+".join(envs)
            in_prod = "prod" in envs and pr["state"] == "merged"
            how = f"แก้ค่าของ env: {', '.join(envs)}"

        pr["deploy"] = {"target": target, "in_prod": in_prod, "why": how,
                        "sha_in_prod_history": sha_seen, "envs_in_paths": envs}
    return {r: {k: v for k, v in info.items() if not k.startswith("_")}
            for r, info in cache.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", action="store_true", help="สัปดาห์ที่แล้ว (จันทร์-อาทิตย์)")
    ap.add_argument("--week", help="เช่น 2026-W35")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--no-prompts", action="store_true")
    ap.add_argument("--out", help="เขียนลงไฟล์แทน stdout")
    a = ap.parse_args()

    since, until, label = resolve_range(a)
    print(f"[recap] ช่วง {since} ถึง {until} ({label})", file=sys.stderr)

    if not run(["gh", "auth", "token"]).strip():
        print("[recap] gh ยังไม่ได้ล็อกอิน — ข้อมูล GitHub จะว่าง", file=sys.stderr)

    authored = collect_prs(since, until, "--author")
    reviewed = [p for p in collect_prs(since, until, "--reviewed-by")
                if p["author"] != GH_LOGIN]
    deploy_by_repo = annotate_deploy(authored)
    issues = collect_issues(since, until)
    commits = collect_commits(since, until)
    prompts = [] if a.no_prompts else collect_prompts(since, until)

    data = {
        "week": label,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "totals": {
            "prs_authored": len(authored),
            "prs_merged": sum(1 for p in authored if p["state"] == "merged"),
            "prs_reviewed": len(reviewed),
            "issues_touched": len(issues),
            "repos_with_commits": len(commits),
            "commits": sum(len(r["commits"]) for r in commits),
            "prompts": sum(p["count"] for p in prompts),
            "landed_in_prod": sum(1 for p in authored if p["deploy"]["in_prod"]),
            "waiting_on_dev": sum(1 for p in authored
                                  if p["deploy"]["target"] == "dev"
                                  and not p["deploy"]["in_prod"]),
        },
        "deploy_by_repo": deploy_by_repo,
        "prs_authored": authored,
        "prs_reviewed": reviewed,
        "issues": issues,
        "local_commits": commits,
        "prompts_by_project": prompts,
    }

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(text)
        print(f"[recap] เขียนลง {a.out}", file=sys.stderr)
        print(json.dumps(data["totals"], ensure_ascii=False), file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
