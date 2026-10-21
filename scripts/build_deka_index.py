#!/usr/bin/env python3
"""สร้าง corpus/deka_cite_index.json.gz จากข้อมูลเปิด phoneee/thai-legal-corpus (CC-BY 4.0)

คนรับสกิลไม่ต้องรันไฟล์นี้ (ดัชนีแนบมาแล้ว) ใช้เมื่ออยากอัปเดตดัชนีเอง:

  curl -L -o deka_citations.jsonl \\
    https://huggingface.co/datasets/phoneee/thai-legal-corpus/resolve/main/metadata/deka_citations.jsonl
  python3 build_deka_index.py deka_citations.jsonl

เก็บเฉพาะ "เลขฎีกา + มาตราที่อ้าง" (ข้อเท็จจริง) ไม่เก็บเนื้อคำพิพากษา
แถวที่มีแค่เลขเอกสารภายในระบบศาล (ไม่มีเลข X/YYYY) หรือปีผิดช่วง ตัดทิ้ง เพราะอ้างในสำนวนไม่ได้
เลขมาตราจัดรูปด้วย _text.norm_section ตัวเดียวกับฝั่งค้น (ไม่งั้น "340ตรี" กับ "340 ตรี" ไม่เจอกัน)
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _text import canon_law, fix_console, law_key, norm_section, to_arabic  # noqa: E402

fix_console()

OUT = Path(__file__).resolve().parent.parent / "corpus" / "deka_cite_index.json.gz"
CASE_RE = re.compile(r"^\d{1,6}/\d{4}$")
YEAR_MIN, YEAR_MAX = 2400, 2600   # นอกช่วงนี้ = ข้อมูลต้นทางเสีย (เจอ 1549/1549, 2015/2015)


def split_cite(s: str) -> list[tuple[str, str]]:
    """'ป.อ. มาตรา 7, 224' → [('ป.อ.', '7'), ('ป.อ.', '224')]"""
    if "มาตรา" not in s:
        return []
    law, no = s.rsplit("มาตรา", 1)
    law = canon_law(law)
    return [(law, n) for n in norm_section(no)] if law else []


def build(src: Path) -> dict:
    laws: dict[str, int] = {}            # ชื่อที่เก็บ → index
    by_key: dict[str, int] = {}          # law_key → index (ชื่อต่างกันแค่ช่องว่าง = ฉบับเดียวกัน)
    cases: dict[str, list] = {}          # case_id → [year, set(sec)]
    skipped = 0
    for line in src.open(encoding="utf-8"):
        r = json.loads(line)
        case = to_arabic(r.get("case_id") or "").strip()
        if not CASE_RE.match(case) or not YEAR_MIN <= int(case.split("/")[1]) <= YEAR_MAX:
            skipped += 1
            continue
        entry = cases.setdefault(case, [int(case.split("/")[1]), set()])
        for s in r.get("sections_cited") or []:
            for law, no in split_cite(s):
                li = by_key.setdefault(law_key(law), len(by_key))
                if li == len(laws):
                    laws[law] = li
                entry[1].add(f"{li}:{no}")
    return {
        "meta": {
            "source": "phoneee/thai-legal-corpus metadata/deka_citations.jsonl",
            "source_url": "https://huggingface.co/datasets/phoneee/thai-legal-corpus",
            "license": "CC-BY 4.0 (ต้นทางข้อมูล: deka.supremecourt.or.th)",
            "cases": len(cases),
            "skipped_no_case_number": skipped,   # รวมแถวที่ปีผิดช่วง
        },
        "laws": list(laws),
        "cases": [[c, y, sorted(s)] for c, (y, s) in cases.items()],
    }


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    data = build(Path(sys.argv[1]))
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    m = data["meta"]
    print(f"เขียน {OUT.name}: {m['cases']:,} เลขฎีกา · {len(data['laws']):,} กฎหมาย · "
          f"ตัด {m['skipped_no_case_number']:,} แถวที่ไม่มีเลขฎีกา/ปีผิด · {OUT.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    main()
