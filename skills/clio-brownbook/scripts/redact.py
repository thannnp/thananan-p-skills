#!/usr/bin/env python3
"""กรองข้อมูลดิบให้ปลอดภัยพอจะวางไว้ใน repo ให้ Hermes อ่านทีหลัง

ตัดสองอย่างทิ้ง เพราะสองอย่างนี้คือของที่ห้ามหลุดไปถึงโมเดลฝั่งนั้น
  1. เนื้อ PR และเนื้อ issue — เป็นร้อยแก้วก็จริง แต่มักมีบล็อกโค้ดกับค่า config ปนมา
  2. ข้อความที่เจ้าของพิมพ์คุยกับผู้ช่วย — มีอะไรอยู่ในนั้นบ้างไม่มีใครรับประกันได้

ที่เหลือไว้คือชื่อ PR สถานะ ชื่อไฟล์ จำนวนบรรทัด และปลายทาง dev/prod
ซึ่งพอให้เขียนสรุปได้ระดับหนึ่งโดยไม่ต้องเห็นโค้ดสักบรรทัด

    redact.py recap-W35.json raw-W35.json
"""
from __future__ import annotations

import json
import sys

DROP_KEYS = ("body",)


def scrub(items: list[dict]) -> list[dict]:
    out = []
    for item in items:
        clean = {k: v for k, v in item.items() if k not in DROP_KEYS}
        out.append(clean)
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    d = json.load(open(src))

    d["prs_authored"] = scrub(d.get("prs_authored", []))
    d["prs_reviewed"] = scrub(d.get("prs_reviewed", []))
    d["issues"] = scrub(d.get("issues", []))
    # ทิ้งทั้งก้อน เหลือไว้แค่ตัวเลขว่าสัปดาห์นั้นคุยกันกี่ครั้ง ที่โปรเจกต์ไหน
    d["prompts_by_project"] = [
        {"project": p["project"], "count": p["count"]}
        for p in d.get("prompts_by_project", [])
    ]
    d["redacted"] = {
        "note": "ตัดเนื้อ PR/issue และข้อความที่เจ้าของพิมพ์ออกแล้ว",
        "kept": "ชื่อ PR, สถานะ, ชื่อไฟล์, จำนวนบรรทัด, ปลายทาง dev/prod, ชื่อ commit",
    }

    with open(dst, "w") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)

    left = sum(1 for p in d["prs_authored"] if p.get("body"))
    if left:
        print(f"กรองไม่หมด ยังเหลือ body {left} อัน", file=sys.stderr)
        return 1
    print(f"เขียน {dst} แล้ว", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
