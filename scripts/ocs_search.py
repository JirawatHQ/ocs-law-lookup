#!/usr/bin/env python3
"""ค้นกฎหมายไทยจาก ocs.go.th (สำนักงานคณะกรรมการกฤษฎีกา) — แหล่งทางการ

  python3 ocs_search.py "ฉ้อโกงประชาชน"
  python3 ocs_search.py "ตำรวจแห่งชาติ" -n 5 --title-only
  python3 ocs_search.py "เครื่องสำอาง" --tab comment     # ความเห็นกฤษฎีกา
  python3 ocs_search.py "" --category 1D -n 50           # ประมวลกฎหมายทั้งหมด
  python3 ocs_search.py "ยาเสพติด" --json                # JSON ดิบ

ผลที่ได้ต่อฉบับ:
  lawNameTh     ชื่อกฎหมาย
  contentlaw    สรุปย่อ (ไฮไลต์คำที่ match)
  fileUUID      ลิงก์ PDF ตัวบทเต็ม (พ.ร.บ. มี / ประมวลกฎหมายไม่มี)
  encTimelineID ใช้กับ ocs_getdoc.py เพื่อดึงตัวบทรายมาตรา
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import HttpError, post_json  # noqa: E402

# Windows: console เริ่มต้นเป็น cp874 → print ภาษาไทยแล้ว UnicodeEncodeError ทันที
# (macOS/Linux เป็น UTF-8 อยู่แล้ว บรรทัดนี้ไม่มีผล)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

API = "https://www.ocs.go.th/searchlaw/indexs/list_table_search"
PDF_BASE = "https://www.ocs.go.th/downloadfile/"


def search(q: str, *, tab: str = "law", content: int = 1, category: str = "",
           perpage: int = 10, page: int = 1, timeout: int = 30) -> dict:
    fields = {
        "query[q]": q,
        "query[tab_type]": tab,          # law = ตัวบท | comment = ความเห็นกฤษฎีกา
        "query[content]": content,       # 1 = ค้น full-text, 0 = ค้นเฉพาะชื่อ
        "query[sort]": "date-desc",
        "query[stateName]": "01,02",     # ใช้บังคับ / รอใช้บังคับ
        "query[topic]": "1",
        "pagination[page]": page,
        "pagination[perpage]": perpage,
    }
    if category:
        fields["query[lawCategoryName]"] = category   # 1D = ประมวลกฎหมาย
    return post_json(
        API,
        form=fields,
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.ocs.go.th/searchlaw",
        },
        timeout=timeout,
    )


def clean(text: str, limit: int = 300) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", help="คำค้น (ใส่ \"\" = ทั้งหมด)")
    ap.add_argument("-n", "--num", type=int, default=10, help="จำนวนผล (default 10)")
    ap.add_argument("-p", "--page", type=int, default=1)
    ap.add_argument("--tab", choices=["law", "comment"], default="law")
    ap.add_argument("--category", default="", help="รหัสหมวด เช่น 1D = ประมวลกฎหมาย")
    ap.add_argument("--title-only", action="store_true", help="ค้นเฉพาะชื่อกฎหมาย ไม่ค้นเนื้อ")
    ap.add_argument("--json", action="store_true", help="พิมพ์ JSON ดิบ")
    args = ap.parse_args()

    try:
        res = search(args.query, tab=args.tab, content=0 if args.title_only else 1,
                     category=args.category, perpage=args.num, page=args.page)
    except HttpError as exc:
        print(f"ค้นไม่สำเร็จ: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0

    meta = res.get("meta", {})
    rows = res.get("data", []) or []
    print(f"พบ {meta.get('total', '?')} ฉบับ (หน้า {meta.get('page', args.page)}/{meta.get('pages', '?')}) "
          f"— แสดง {len(rows)}\n")

    for i, row in enumerate(rows, 1):
        # lawNameTh มี <mark> ครอบคำที่ match ต้องถอดออกก่อน
        print(f"[{i}] {clean(row.get('lawNameTh', '-'), 200)}  ({row.get('year', '-')})")
        summary = clean(row.get("contentlaw", ""))
        if summary:
            print(f"    {summary}")
        if row.get("fileUUID"):
            uuid = row["fileUUID"]
            # บางฉบับ fileUUID เป็น URL เต็มมาแล้ว บางฉบับเป็น token ล้วน
            print(f"    PDF: {uuid if uuid.startswith('http') else PDF_BASE + uuid}")
        if row.get("encTimelineID"):
            print(f"    ตัวบทรายมาตรา: python3 ocs_getdoc.py {row['encTimelineID']} -o out.md")
        kids = row.get("childrens") or []
        if kids:
            print(f"    กฎลูก {len(kids)} ฉบับ: " + "; ".join(k.get("lawNameTh", "-") for k in kids[:3])
                  + ("…" if len(kids) > 3 else ""))
        print()

    print("อ้างอิงทุกครั้ง: ชื่อฉบับ + ปี + ลิงก์ — ห้ามสรุปมาตราจากความจำ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
