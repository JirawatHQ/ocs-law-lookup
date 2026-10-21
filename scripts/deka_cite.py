#!/usr/bin/env python3
"""ฎีกาเรื่องไหนอ้างมาตรานี้บ้าง — ค้นดัชนีในเครื่อง ตอบทันที ไม่ต้องต่อเน็ต

  python3 deka_cite.py 341                       ฎีกาที่อ้าง ป.อ. ม.341 (ค่าตั้งต้น = ป.อ.)
  python3 deka_cite.py 341 --with 343            อ้างทั้ง 341 และ 343 (ฉ้อโกงประชาชน)
  python3 deka_cite.py 14 --law คอมพิวเตอร์      กฎหมายอื่น: ใส่บางส่วนของชื่อ
  python3 deka_cite.py 87 --law ป.วิ.อาญา --year 2560
  python3 deka_cite.py --case 4920/2567          ฎีกาเรื่องนี้อ้างมาตราอะไรบ้าง
  python3 deka_cite.py --laws มาตรฐาน            ดูชื่อกฎหมายที่มีในดัชนี

รับ "ม.๓๔๑", "340ตรี", "341 (1)" ได้หมด (อนุมาตรา/วรรค ถูกตัด เพราะดัชนีเก็บระดับมาตรา)
ได้แค่ "เลขฎีกา + มาตราที่อ้าง" ตัวคำพิพากษาต้องดึงจากเว็บศาล:
  python3 scripts/deka_search.py --deka-no <เลข> --full
ดัชนีไม่ครบทุกเรื่อง (ดู README) ไม่เจอในดัชนี ≠ ไม่มีฎีกา
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _text import fix_console, law_key, norm_section, to_arabic  # noqa: E402

fix_console()

INDEX = Path(__file__).resolve().parent.parent / "corpus" / "deka_cite_index.json.gz"
FULL_TEXT_HINT = "ตัวเต็ม: python3 scripts/deka_search.py --deka-no <เลข> --full"

# ดัชนีเก็บประมวลเป็นชื่อย่อ คนพิมพ์ชื่อเต็มกันเป็นปกติ → แปลงก่อน
LAW_ALIASES = {
    "ประมวลกฎหมายอาญา": "ป.อ.", "ป.อาญา": "ป.อ.",
    "ประมวลกฎหมายวิธีพิจารณาความอาญา": "ป.วิ.อ.", "ป.วิ.อาญา": "ป.วิ.อ.",
    "ประมวลกฎหมายแพ่งและพาณิชย์": "ป.พ.พ.",
    "ประมวลกฎหมายวิธีพิจารณาความแพ่ง": "ป.วิ.พ.", "ป.วิ.แพ่ง": "ป.วิ.พ.",
    "ประมวลรัษฎากร": "ป.รัษฎากร",
    "ประมวลกฎหมายที่ดิน": "ป.ที่ดิน",
}


def load() -> dict:
    with gzip.open(INDEX, "rt", encoding="utf-8") as f:
        return json.load(f)


def law_ids(laws: list[str], pattern: str) -> list[int]:
    """ชื่อเต็ม/ชื่อย่อ/บางส่วนของชื่อ → index ในดัชนี (ไม่สนช่องว่าง)"""
    key = law_key(pattern)
    key = law_key(next((v for k, v in LAW_ALIASES.items() if law_key(k) == key), pattern))
    keys = [law_key(name) for name in laws]
    if key in keys:                          # ตรงเป๊ะชนะ ('ป.อ.' ไม่ควรไปเจอฉบับอื่นที่มีคำนี้)
        return [keys.index(key)]
    return [i for i, k in enumerate(keys) if key in k]


def cases_citing(data: dict, ids: list[int], no: str) -> set[str]:
    want = {f"{i}:{no}" for i in ids}
    return {c for c, _, secs in data["cases"] if want.intersection(secs)}


def label(laws: list[str], sec: str) -> str:
    li, no = sec.split(":", 1)
    return f"{laws[int(li)]} ม.{no}"


def main() -> int:
    ap = argparse.ArgumentParser(description="ฎีกาที่อ้างมาตรา (ดัชนีในเครื่อง)")
    ap.add_argument("section", nargs="*", help="เลขมาตรา เช่น 341, 277 ทวิ, ม.๓๔๑")
    ap.add_argument("--law", default="ป.อ.", help="ชื่อกฎหมาย (ชื่อเต็ม ชื่อย่อ หรือบางส่วน) ค่าตั้งต้น ป.อ.")
    ap.add_argument("--with", dest="also", action="append", default=[],
                    help="ต้องอ้างมาตรานี้ด้วย (กฎหมายเดียวกัน) ใส่ซ้ำได้")
    ap.add_argument("--year", type=int, help="ตั้งแต่ปี พ.ศ. นี้")
    ap.add_argument("-n", "--num", type=int, default=15, help="จำนวนที่แสดง (default 15)")
    ap.add_argument("--case", help="ดูว่าฎีกาเลขนี้อ้างมาตราอะไร")
    ap.add_argument("--laws", metavar="คำ", help="ค้นชื่อกฎหมายที่มีในดัชนี")
    a = ap.parse_args()
    if a.num < 0:
        ap.error("-n ต้องเป็น 0 ขึ้นไป")

    data = load()
    laws = data["laws"]
    by_case = {c: (y, secs) for c, y, secs in data["cases"]}

    if a.laws is not None:
        hits = [laws[i] for i in law_ids(laws, a.laws)]
        if not hits:
            print(f"ไม่มีกฎหมายที่ชื่อมีคำว่า '{a.laws}' ในดัชนี")
            return 1
        print("\n".join(hits))
        return 0
    if a.case:
        case = to_arabic(a.case).strip()
        if case not in by_case:
            print(f"ไม่มี {case} ในดัชนี (ไม่ได้แปลว่าไม่มีฎีกานี้ — ลอง deka_search.py --deka-no {case})")
            return 1
        print(f"คำพิพากษาศาลฎีกาที่ {case} อ้าง:")
        for s in by_case[case][1]:
            print("  " + label(laws, s))
        return 0
    if not a.section:
        ap.error("ใส่เลขมาตรา หรือใช้ --case / --laws")

    ids = law_ids(laws, a.law)
    if not ids:
        print(f"ไม่มีกฎหมายที่ชื่อมีคำว่า '{a.law}' ในดัชนี — ดูชื่อด้วย --laws <คำ>", file=sys.stderr)
        return 1
    nos = norm_section(" ".join(a.section)) + [n for x in a.also for n in norm_section(x)]
    if not nos:
        ap.error(f"อ่านเลขมาตราจาก '{' '.join(a.section)}' ไม่ออก")
    found = cases_citing(data, ids, nos[0])
    for no in nos[1:]:
        found &= cases_citing(data, ids, no)

    names = ", ".join(laws[i] for i in ids[:3]) + (" …" if len(ids) > 3 else "")
    title = " + ".join(f"ม.{n}" for n in nos)
    if found and a.year:
        before = len(found)
        found = {c for c in found if by_case[c][0] >= a.year}
        if not found:
            print(f"มี {before:,} เรื่องที่อ้าง {title} ({names}) แต่ไม่มีเรื่องไหนตั้งแต่ปี {a.year}")
            return 1
    if not found:
        print(f"ไม่พบฎีกาในดัชนีที่อ้าง {title} ({names}) — ดัชนีไม่ครบ "
              "ลอง python3 scripts/deka_search.py --section <เลข>")
        return 1

    rows = sorted(found, key=lambda c: (by_case[c][0], int(c.split("/")[0])), reverse=True)
    print(f"ฎีกาที่อ้าง {title} ({names}): {len(rows):,} เรื่อง ใหม่สุดก่อน")
    wanted = {f"{i}:{n}" for i in ids for n in nos}
    for c in rows[:a.num]:
        others = [label(laws, s) for s in by_case[c][1] if s not in wanted]
        extra = f"  · อ้างร่วม: {', '.join(others[:5])}{' …' if len(others) > 5 else ''}" if others else ""
        print(f"  {c}{extra}")
    if len(rows) > a.num:
        print(f"  … อีก {len(rows) - a.num:,} เรื่อง (-n เพื่อดูเพิ่ม)")
    print(f"{FULL_TEXT_HINT} · ที่มา: phoneee/thai-legal-corpus (CC-BY 4.0) ไม่ครบทุกเรื่อง")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
