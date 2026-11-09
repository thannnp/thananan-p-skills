#!/usr/bin/env python3
"""ใส่ข้อมูลสัปดาห์ลงหน้าประชุม โดยไม่แตะดีไซน์

    fill_meeting.py report.json out.html     # อ่าน meeting/page.html แทนที่ก้อน <script id="report"> ด้วย report.json
"""
import json, os, re, sys

def fill(page: str, data: dict) -> str:
    body = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")  # กัน </script> ในข้อความปิดแท็กก่อน
    out, n = re.subn(r'(<script id="report" type="application/json">)[\s\S]*?(</script>)',
                     lambda m: m.group(1) + "\n" + body + "\n" + m.group(2), page, count=1)
    assert n == 1, "ไม่เจอก้อน report ใน page.html"
    return out

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    tpl = os.path.join(os.path.dirname(__file__), "..", "meeting", "page.html")
    data = json.load(open(sys.argv[1]))
    for k in ("week", "range", "totals", "projects", "offgit", "next"):
        assert k in data, f"report.json ขาด {k}"
    open(sys.argv[2], "w").write(fill(open(tpl).read(), data))
    print("เขียน", sys.argv[2])
