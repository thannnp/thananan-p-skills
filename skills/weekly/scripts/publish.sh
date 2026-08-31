#!/usr/bin/env bash
# เอาโน้ตสรุปสัปดาห์ขึ้น repo worklog ส่วนตัว ให้ Hermes อ่านต่อได้
#
#   publish.sh "~/Documents/Obsidian Vault/Dev/Recap of completed tasks/2026-W35.md"
#
# repo ต้องเป็น private เพราะเนื้อในเป็นรายละเอียดงานบริษัท
set -euo pipefail

NOTE="${1:?ต้องบอกไฟล์โน้ตที่จะอัป}"
REPO="${WORKLOG_REPO:-thannnp/worklog}"
CLONE="${WORKLOG_CLONE:-$HOME/.cache/worklog-repo}"

[ -f "$NOTE" ] || { echo "ไม่เจอไฟล์: $NOTE" >&2; exit 1; }

if ! gh repo view "$REPO" >/dev/null 2>&1; then
  cat >&2 <<MSG
ยังไม่มี repo $REPO
สร้างก่อนด้วย (ต้องเป็น private):
  gh repo create $REPO --private --description "บันทึกงานรายสัปดาห์"
MSG
  exit 1
fi

if [ "$(gh repo view "$REPO" --json isPrivate --jq .isPrivate)" != "true" ]; then
  echo "หยุดก่อน — $REPO เป็น public โน้ตนี้มีรายละเอียดงานบริษัท" >&2
  exit 1
fi

if [ ! -d "$CLONE/.git" ]; then
  mkdir -p "$(dirname "$CLONE")"
  gh repo clone "$REPO" "$CLONE" -- --quiet
fi

git -C "$CLONE" pull --quiet --rebase 2>/dev/null || true

BASE="$(basename "$NOTE")"          # 2026-W35.md
YEAR="${BASE%%-*}"                  # 2026
mkdir -p "$CLONE/$YEAR"
cp "$NOTE" "$CLONE/$YEAR/$BASE"

git -C "$CLONE" add "$YEAR/$BASE"
if git -C "$CLONE" diff --cached --quiet; then
  echo "ไม่มีอะไรเปลี่ยน — $YEAR/$BASE เหมือนเดิม"
  exit 0
fi

git -C "$CLONE" commit --quiet -m "worklog: ${BASE%.md}"
git -C "$CLONE" push --quiet
echo "ขึ้นแล้ว: https://github.com/$REPO/blob/HEAD/$YEAR/$BASE"
