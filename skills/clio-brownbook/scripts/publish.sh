#!/usr/bin/env bash
# เอาโน้ตสัปดาห์ขึ้น repo clio ให้ clio-echo อ่านต่อได้
#
#   publish.sh <โน้ต.md> [ข้อมูลดิบที่กรองแล้ว.json]
#
# ไฟล์ json ใส่หรือไม่ใส่ก็ได้ ถ้าใส่ต้องเป็นตัวที่ผ่าน redact.py มาแล้วเท่านั้น
set -euo pipefail

NOTE="${1:?ต้องบอกไฟล์โน้ตที่จะอัป}"
RAW="${2:-}"
REPO="${CLIO_REPO:-thannnp/clio}"
CLONE="${CLIO_CLONE:-$HOME/.cache/clio-repo}"

[ -f "$NOTE" ] || { echo "ไม่เจอไฟล์โน้ต: $NOTE" >&2; exit 1; }

if [ "$(gh repo view "$REPO" --json isPrivate --jq .isPrivate 2>/dev/null)" != "true" ]; then
  echo "หยุดก่อน — $REPO ไม่ใช่ private หรือเข้าไม่ได้ ข้างในเป็นรายละเอียดงานบริษัท" >&2
  exit 1
fi

# ข้อมูลดิบต้องผ่านตัวกรองมาแล้ว เช็คซ้ำตรงนี้กันพลาดมือ
if [ -n "$RAW" ]; then
  [ -f "$RAW" ] || { echo "ไม่เจอไฟล์ข้อมูลดิบ: $RAW" >&2; exit 1; }
  if ! grep -q '"redacted"' "$RAW"; then
    echo "หยุดก่อน — $RAW ยังไม่ผ่าน redact.py ในนั้นมีเนื้อ PR กับที่คุณพิมพ์อยู่" >&2
    exit 1
  fi
fi

if [ ! -d "$CLONE/.git" ]; then
  mkdir -p "$(dirname "$CLONE")"
  git clone -q "https://github.com/$REPO.git" "$CLONE"
fi
git -C "$CLONE" pull -q --rebase

BASE="$(basename "$NOTE")"          # 2026-W35.md
YEAR="${BASE%%-*}"                  # 2026
mkdir -p "$CLONE/$YEAR" "$CLONE/raw"
cp "$NOTE" "$CLONE/$YEAR/$BASE"
[ -n "$RAW" ] && cp "$RAW" "$CLONE/raw/${BASE%.md}.json"

git -C "$CLONE" add -A
if git -C "$CLONE" diff --cached --quiet; then
  echo "ไม่มีอะไรเปลี่ยน — $YEAR/$BASE เหมือนเดิมอยู่แล้ว"
  exit 0
fi

git -C "$CLONE" commit -q -m "Add the work log for ${BASE%.md}"
git -C "$CLONE" push -q
echo "ขึ้นแล้ว https://github.com/$REPO/blob/main/$YEAR/$BASE"
