#!/usr/bin/env python3
"""สร้าง corpus/deka_cite_index.json.gz จากข้อมูลเปิด phoneee/thai-legal-corpus (CC-BY 4.0)

คนรับสกิลไม่ต้องรันไฟล์นี้ (ดัชนีแนบมาแล้ว) ใช้เมื่ออยากอัปเดตดัชนีเอง:

  curl -L -o deka_citations.jsonl \\
    https://huggingface.co/datasets/phoneee/thai-legal-corpus/resolve/main/metadata/deka_citations.jsonl
  python3 build_deka_index.py deka_citations.jsonl

เก็บเฉพาะ "เลขฎีกา + มาตราที่อ้าง" (ข้อเท็จจริง) ไม่เก็บเนื้อคำพิพากษา
แถวที่มีแค่เลขเอกสารภายในระบบศาล (ไม่มีเลข X/YYYY) ตัดทิ้ง เพราะอ้างในสำนวนไม่ได้
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(__file__).resolve().parent.parent / "corpus" / "deka_cite_index.json.gz"
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
CASE_RE = re.compile(r"^\d{1,6}/\d{4}$")


def split_cite(s: str) -> tuple[str, str] | None:
    """'ป.อ. มาตรา 341' → ('ป.อ.', '341')"""
    if " มาตรา " not in s:
        return None
    law, no = s.rsplit(" มาตรา ", 1)
    law, no = law.strip(), re.sub(r"\s+", " ", no.translate(THAI_DIGITS)).strip()
    return (law, no) if law and no else None


def build(src: Path) -> dict:
    laws: dict[str, int] = {}
    cases: dict[str, list] = {}          # case_id → [year, set(sec)]
    skipped = 0
    for line in src.open(encoding="utf-8"):
        r = json.loads(line)
        case = (r.get("case_id") or "").translate(THAI_DIGITS).strip()
        if not CASE_RE.match(case):
            skipped += 1
            continue
        entry = cases.setdefault(case, [int(case.split("/")[1]), set()])
        for s in r.get("sections_cited") or []:
            parsed = split_cite(s)
            if parsed:
                li = laws.setdefault(parsed[0], len(laws))
                entry[1].add(f"{li}:{parsed[1]}")
    return {
        "meta": {
            "source": "phoneee/thai-legal-corpus metadata/deka_citations.jsonl",
            "source_url": "https://huggingface.co/datasets/phoneee/thai-legal-corpus",
            "license": "CC-BY 4.0 (ต้นทางข้อมูล: deka.supremecourt.or.th)",
            "cases": len(cases),
            "skipped_no_case_number": skipped,
        },
        "laws": list(laws),
        "cases": [[c, y, sorted(s)] for c, (y, s) in cases.items()],
    }


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    data = build(Path(sys.argv[1]))
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    m = data["meta"]
    print(f"เขียน {OUT.name}: {m['cases']:,} เลขฎีกา · {len(data['laws']):,} กฎหมาย · "
          f"ตัด {m['skipped_no_case_number']:,} แถวที่ไม่มีเลขฎีกา · {OUT.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    main()
