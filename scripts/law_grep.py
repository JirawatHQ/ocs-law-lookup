#!/usr/bin/env python3
"""ค้นตัวบทในเครื่อง (corpus/) — ไม่ต้องต่อเน็ต ตอบได้ทันที

  python3 law_grep.py -s 341                 ดึง ป.อาญา มาตรา 341 เต็ม (ค้นทุกฉบับ)
  python3 law_grep.py -s 87 -f crim          ดึง ป.วิ.อ. มาตรา 87
  python3 law_grep.py -s "277 ทวิ"           มาตราที่มี ทวิ/ตรี
  python3 law_grep.py "ฉ้อโกงประชาชน"        ค้นคำ → รายชื่อมาตราที่เข้าข่าย
  python3 law_grep.py "ปล่อยชั่วคราว" -c 5   ค้นคำ แสดง 5 ผลแรกเต็ม
  python3 law_grep.py --list                 ดูว่ามีตัวบทอะไรบ้าง

รับเลขไทย/อารบิกทั้งคู่ (ม.๓๔๑ = ม.341)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Windows: console เริ่มต้นเป็น cp874 → print ภาษาไทยแล้ว UnicodeEncodeError ทันที
# (macOS/Linux เป็น UTF-8 อยู่แล้ว บรรทัดนี้ไม่มีผล)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def to_arabic(text: str) -> str:
    return text.translate(THAI_DIGITS)


def corpus_files(pattern: str = "") -> list[Path]:
    files = sorted(CORPUS.glob("*.md"))
    if pattern:
        low = pattern.lower()
        files = [f for f in files if low in f.stem.lower()]
    return files


def split_sections(path: Path) -> list[tuple[str, str, str]]:
    """แยกไฟล์เป็น (heading, breadcrumb, body) ต่อมาตรา

    breadcrumb = ภาค/ลักษณะ/หมวด/ส่วน ที่ครอบมาตรานั้นอยู่ — สำคัญเวลาอ้างในสำนวน
    """
    out: list[tuple[str, str, str]] = []
    crumbs: list[str] = []
    heading: str | None = None
    crumb_at_heading = ""
    buf: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("### 〔"):
            kind = re.match(r"### 〔(\S+)", line)
            label = line[4:].replace("〔", "").replace("〕", "").strip()
            if kind:
                # ภาค > ลักษณะ > หมวด > ส่วน — ระดับใหม่ตัดของเดิมที่ลึกกว่า
                order = {"ภาค": 0, "ลักษณะ": 1, "หมวด": 2, "ส่วน": 3}
                depth = order.get(kind.group(1), 3)
                crumbs = crumbs[:depth] + [label]
            continue
        if line.startswith("## "):
            if heading:
                out.append((heading, crumb_at_heading, "\n".join(buf).strip()))
            heading = line[3:].strip()
            crumb_at_heading = " › ".join(crumbs)
            buf = []
            continue
        if line.startswith("# "):
            crumbs = []
            continue
        if heading:
            buf.append(line)

    if heading:
        out.append((heading, crumb_at_heading, "\n".join(buf).strip()))
    return out


MAX_BODY = 4000   # เอกสารสรุป (ระเบียบ/คำสั่ง) มีหัวข้อเดียวยาวหลายพันตัวอักษร


def show(path: Path, heading: str, crumb: str, body: str) -> None:
    print(f"\n=== {path.stem} · {heading}")
    if crumb:
        print(f"    ({crumb})")
    print(body[:MAX_BODY] + ("\n…(ตัดที่ 4,000 ตัวอักษร — เปิดไฟล์เต็มที่ corpus/)"
                             if len(body) > MAX_BODY else ""))


def by_section(number: str, file_filter: str) -> int:
    target = to_arabic(number).strip()
    target_norm = re.sub(r"\s+", " ", target)
    hits = 0
    for path in corpus_files(file_filter):
        for heading, crumb, body in split_sections(path):
            head_no = re.sub(r"^มาตรา\s+", "", heading.split("〔")[0]).strip()
            if re.sub(r"\s+", " ", to_arabic(head_no)) == target_norm:
                show(path, heading, crumb, body)
                hits += 1
    if not hits:
        print(f"ไม่พบมาตรา {number} ใน corpus — ลองค้นออนไลน์: python3 ocs_search.py \"...\"",
              file=sys.stderr)
        return 1
    return 0


def by_keyword(query: str, file_filter: str, full: int) -> int:
    words = [to_arabic(w) for w in query.split()]
    results = []
    for path in corpus_files(file_filter):
        for heading, crumb, body in split_sections(path):
            hay = to_arabic(body)
            if all(w in hay for w in words):
                results.append((path, heading, crumb, body))

    if not results:
        print(f"ไม่พบ \"{query}\" ใน corpus — ลอง: python3 ocs_search.py \"{query}\"", file=sys.stderr)
        return 1

    print(f"พบ {len(results)} รายการ\n")
    for i, (path, heading, crumb, body) in enumerate(results, 1):
        if i <= full:
            show(path, heading, crumb, body)
        else:
            snippet = re.sub(r"\s+", " ", body)[:120]
            print(f"[{i}] {path.stem} · {heading}" + (f"  ({crumb})" if crumb else ""))
            print(f"    {snippet}…")
    if len(results) > full:
        print(f"\n(แสดงเต็ม {full} รายการแรก — เพิ่มด้วย -c N)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?", help="คำค้น")
    ap.add_argument("-s", "--section", help="เลขมาตรา (เช่น 341 หรือ \"277 ทวิ\")")
    ap.add_argument("-f", "--file", default="", help="จำกัดฉบับ (penal / crim / police)")
    ap.add_argument("-c", "--count", type=int, default=3, help="จำนวนผลที่แสดงเต็ม (default 3)")
    ap.add_argument("--list", action="store_true", help="ดูรายชื่อตัวบทที่มีในเครื่อง")
    args = ap.parse_args()

    if args.list:
        for path in corpus_files():
            first = path.read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ")
            n = len(re.findall(r"^## มาตรา ", path.read_text(encoding="utf-8"), re.M))
            print(f"{path.stem:24} {first}  ({n} มาตรา)")
        return 0

    if args.section:
        return by_section(args.section, args.file)
    if args.query:
        return by_keyword(args.query, args.file, args.count)
    ap.error("ต้องระบุคำค้น หรือ -s เลขมาตรา")


if __name__ == "__main__":
    raise SystemExit(main())
