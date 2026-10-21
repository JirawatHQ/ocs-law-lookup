#!/usr/bin/env python3
"""ฎีกาเรื่องไหนอ้างมาตรานี้บ้าง — ค้นดัชนีในเครื่อง ตอบทันที ไม่ต้องต่อเน็ต

  python3 deka_cite.py 341                       ฎีกาที่อ้าง ป.อ. ม.341 (ค่าตั้งต้น = ป.อ.)
  python3 deka_cite.py 341 --with 343            อ้างทั้ง 341 และ 343 (ฉ้อโกงประชาชน)
  python3 deka_cite.py 14 --law คอมพิวเตอร์      กฎหมายอื่น: ใส่บางส่วนของชื่อ
  python3 deka_cite.py 87 --law ป.วิ.อ. --year 2560
  python3 deka_cite.py --case 4920/2567          ฎีกาเรื่องนี้อ้างมาตราอะไรบ้าง
  python3 deka_cite.py --laws มาตรฐาน            ดูชื่อกฎหมายที่มีในดัชนี

ได้แค่ "เลขฎีกา + มาตราที่อ้าง" ตัวคำพิพากษาต้องดึงจากเว็บศาล:
  python3 deka_search.py --deka-no <เลข> --full
ดัชนีไม่ครบทุกเรื่อง (ดู README) ไม่เจอในดัชนี ≠ ไม่มีฎีกา
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

INDEX = Path(__file__).resolve().parent.parent / "corpus" / "deka_cite_index.json.gz"
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def load() -> dict:
    with gzip.open(INDEX, "rt", encoding="utf-8") as f:
        return json.load(f)


def norm_no(no: str) -> str:
    """'๓๔๑' → '341', 'มาตรา 277ทวิ' → '277 ทวิ'"""
    no = no.translate(THAI_DIGITS).replace("มาตรา", "").replace("ม.", "")
    no = re.sub(r"(\d)(ทวิ|ตรี|จัตวา|เบญจ|ฉ)", r"\1 \2", no)
    return re.sub(r"\s+", " ", no).strip()


def base_no(no: str) -> str:
    """'3 (1)' → '3' — ค้น 3 ให้เจอ 3 (1) ด้วย; '160 ทวิ/1' คงไว้"""
    return no.split(" (")[0].strip()


def law_ids(laws: list[str], pattern: str) -> list[int]:
    if pattern in laws:                     # ตรงเป๊ะชนะ ('ป.อ.' ไม่ควรไปเจอ 'ป.อ.ม.' อื่น)
        return [laws.index(pattern)]
    return [i for i, name in enumerate(laws) if pattern in name]


def cases_citing(data: dict, ids: list[int], no: str) -> set[str]:
    want = {f"{i}:{no}" for i in ids}
    return {c for c, _, secs in data["cases"]
            if any(f"{s.split(':', 1)[0]}:{base_no(s.split(':', 1)[1])}" in want for s in secs)}


def label(laws: list[str], sec: str) -> str:
    li, no = sec.split(":", 1)
    return f"{laws[int(li)]} ม.{no}"


def main() -> None:
    ap = argparse.ArgumentParser(description="ฎีกาที่อ้างมาตรา (ดัชนีในเครื่อง)")
    ap.add_argument("section", nargs="*", help="เลขมาตรา เช่น 341, 277 ทวิ, ๓๔๑")
    ap.add_argument("--law", default="ป.อ.", help="ชื่อกฎหมาย (บางส่วนก็ได้) ค่าตั้งต้น ป.อ.")
    ap.add_argument("--with", dest="also", action="append", default=[],
                    help="ต้องอ้างมาตรานี้ด้วย (กฎหมายเดียวกัน) ใส่ซ้ำได้")
    ap.add_argument("--year", type=int, help="ตั้งแต่ปี พ.ศ. นี้")
    ap.add_argument("-n", "--num", type=int, default=15, help="จำนวนที่แสดง (default 15)")
    ap.add_argument("--case", help="ดูว่าฎีกาเลขนี้อ้างมาตราอะไร")
    ap.add_argument("--laws", metavar="คำ", help="ค้นชื่อกฎหมายที่มีในดัชนี")
    a = ap.parse_args()

    data = load()
    laws = data["laws"]
    by_case = {c: (y, secs) for c, y, secs in data["cases"]}

    if a.laws is not None:
        hits = [n for n in laws if a.laws in n]
        print("\n".join(hits) if hits else f"ไม่มีกฎหมายที่ชื่อมีคำว่า '{a.laws}' ในดัชนี")
        return
    if a.case:
        case = a.case.translate(THAI_DIGITS).strip()
        if case not in by_case:
            print(f"ไม่มี {case} ในดัชนี (ไม่ได้แปลว่าไม่มีฎีกานี้ — ลอง deka_search.py --deka-no {case})")
            return
        print(f"คำพิพากษาศาลฎีกาที่ {case} อ้าง:")
        for s in by_case[case][1]:
            print("  " + label(laws, s))
        return
    if not a.section:
        ap.error("ใส่เลขมาตรา หรือใช้ --case / --laws")

    ids = law_ids(laws, a.law)
    if not ids:
        sys.exit(f"ไม่มีกฎหมายที่ชื่อมีคำว่า '{a.law}' ในดัชนี — ดูชื่อด้วย --laws <คำ>")
    nos = [norm_no(" ".join(a.section))] + [norm_no(x) for x in a.also]
    found = cases_citing(data, ids, nos[0])
    for no in nos[1:]:
        found &= cases_citing(data, ids, no)
    if a.year:
        found = {c for c in found if by_case[c][0] >= a.year}

    names = ", ".join(laws[i] for i in ids[:3]) + (" …" if len(ids) > 3 else "")
    title = " + ".join(f"ม.{n}" for n in nos)
    if not found:
        print(f"ไม่พบฎีกาในดัชนีที่อ้าง {title} ({names}) — ดัชนีไม่ครบ ลอง deka_search.py --section")
        return
    rows = sorted(found, key=lambda c: (by_case[c][0], int(c.split("/")[0])), reverse=True)
    print(f"ฎีกาที่อ้าง {title} ({names}): {len(rows):,} เรื่อง ใหม่สุดก่อน")
    for c in rows[:a.num]:
        others = [label(laws, s) for s in by_case[c][1]
                  if int(s.split(":", 1)[0]) not in ids or base_no(s.split(":", 1)[1]) not in nos]
        extra = f"  · อ้างร่วม: {', '.join(others[:5])}{' …' if len(others) > 5 else ''}" if others else ""
        print(f"  {c}{extra}")
    if len(rows) > a.num:
        print(f"  … อีก {len(rows) - a.num:,} เรื่อง (-n เพื่อดูเพิ่ม)")
    print("ตัวเต็ม: python3 deka_search.py --deka-no <เลข> --full · "
          "ที่มา: phoneee/thai-legal-corpus (CC-BY 4.0) ไม่ครบทุกเรื่อง")


if __name__ == "__main__":
    main()
