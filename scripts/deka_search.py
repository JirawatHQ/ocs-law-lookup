#!/usr/bin/env python3
"""ค้นคำพิพากษาศาลฎีกา จาก deka.supremecourt.or.th (ศาลฎีกา)

ocs.go.th ไม่มีฎีกา — คนละแหล่งกัน ตัวนี้ใช้เมื่อถามถึงแนวคำวินิจฉัย/บรรทัดฐาน

  python3 deka_search.py "ฉ้อโกงประชาชน"
  python3 deka_search.py "รับของโจร บัญชีเงินฝาก"    # หลายคำ = AND
  python3 deka_search.py --section 341               # ค้นตามมาตรา
  python3 deka_search.py --deka-no 485/2567          # ค้นตามเลขฎีกา
  python3 deka_search.py "ฉ้อโกง" --full             # พิมพ์คำวินิจฉัยตัวเต็ม
  python3 deka_search.py "ฉ้อโกง" --year 2560 2569   # จำกัดช่วงปี พ.ศ.

ข้อควรระวัง:
- ค้นทีละเรื่องที่ใช้จริงในคดี ห้าม bulk-scrape (เว็บศาล ลิขสิทธิ์ศาลฎีกา)
- ไม่พบ = บอกว่าไม่พบ ห้ามแต่งเลขฎีกา
- สคริปต์ยิง control query เทียบทุกครั้ง กันกับดัก session-replay (ดู references/deka_api.md)
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Windows: console เริ่มต้นเป็น cp874 → print ภาษาไทยแล้ว UnicodeEncodeError ทันที
# (macOS/Linux เป็น UTF-8 อยู่แล้ว บรรทัดนี้ไม่มีผล)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://deka.supremecourt.or.th"
CONTROL_QUERY = "ลิขสิทธิ์"   # คำที่ไม่เกี่ยวกับคำค้นจริง ใช้ตรวจว่าเซิร์ฟเวอร์ตอบตามที่ส่งไปจริง
# ⚠ ไม่ส่ง User-Agent = เซิร์ฟเวอร์ไม่ตอบเลย (timeout/connection reset) ไม่ใช่เน็ตเสีย
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _curl(args: list[str], timeout: int = 280) -> str:
    if not shutil.which("curl"):
        sys.exit("ต้องมี curl ในเครื่อง (urllib โดน reset ที่ TLS handshake กับเว็บนี้)")
    # encoding="utf-8" จำเป็น: บน Windows text=True จะถอด HTML ด้วย cp874 → เนื้อคำพิพากษาเพี้ยน
    # แบบไม่ error (พังเงียบ — ได้ผลลัพธ์ผิดโดยไม่รู้ตัว)
    proc = subprocess.run(["curl", "-sS", "--max-time", str(timeout), "-H", f"User-Agent: {UA}", *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"curl ล้มเหลว ({proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


def query(fields: dict, cookie_jar: Path, retries: int = 2) -> str:
    """POST /search — ต้องมี session cookie ก่อน ไม่งั้นคืนผลค้างจาก session เดิม"""
    if not cookie_jar.exists() or cookie_jar.stat().st_size == 0:
        _curl(["-c", str(cookie_jar), f"{BASE}/"])
    data = "&".join(f"{k}={v}" for k, v in _encode(fields).items())
    last = ""
    for attempt in range(retries + 1):
        html_text = _curl(["-c", str(cookie_jar), "-b", str(cookie_jar),
                           "-X", "POST", f"{BASE}/search", "--data", data,
                           "-H", "Content-Type: application/x-www-form-urlencoded"])
        if html_text.strip():
            return html_text
        last = "คำตอบว่าง (เซิร์ฟเวอร์ช้าหรือ timeout)"
    raise RuntimeError(f"ค้น deka ไม่สำเร็จ: {last}")


def _encode(fields: dict) -> dict:
    from urllib.parse import quote
    return {k: quote(str(v)) for k, v in fields.items()}


def build_fields(*, word: str = "", section: str = "", deka_no: str = "",
                 year_from: str = "", year_to: str = "", full: bool = False) -> dict:
    fields = {
        "search_doctype": 1,            # 1 = คำพิพากษาศาลฎีกา
        "search_type": 2 if full else 1,  # 1 = ฉบับย่อ, 2 = ฉบับเต็ม
        "start": "true",                # ⚠ ต้องเป็น true ไม่ใช่ตัวเลข ไม่งั้นได้ผลค้างใน session
        "search_form_type": "basic",
    }
    if word:
        fields["search_word"] = word
    if section:
        fields["adv_search_law_section"] = section
        fields["search_form_type"] = "advance"
    if deka_no:
        fields["adv_search_deka_no"] = deka_no
        fields["search_form_type"] = "advance"
    if year_from:
        fields["search_deka_start_year"] = year_from
    if year_to:
        fields["search_deka_end_year"] = year_to
    return fields


def strip_tags(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse(html_text: str) -> list[dict]:
    """ผลค้นฝังทั้งย่อและตัวเต็มมาในหน้าเลย ไม่ต้องยิง detail แยก

    ผูกเลขฎีกากับ docid ผ่าน text_bookmark_name_<docid> — ห้ามจับคู่ตามลำดับที่เจอ
    เพราะเลขฎีกาปรากฏซ้ำหลายที่ต่อรายการ (list + บล็อกสำหรับพิมพ์) แล้วจะเลื่อนคู่ผิด
    """
    numbers = {
        m.group(1): m.group(2).strip()
        for m in re.finditer(r'id="text_bookmark_name_(\d+)"\s+value="คำพิพากษาศาลฎีกาที่\s*([^"]+)"',
                             html_text)
    }

    results: list[dict] = []
    index: dict[str, dict] = {}
    # บล็อกเนื้อหาเป็น <li ...>…</li> (ไม่ใช่ div) — ปิดผิด tag จะกินเนื้อรายการถัดไปมาด้วย
    for m in re.finditer(r'id="(short|long)_text_docid_(\d+)"[^>]*>(.*?)</li>', html_text, re.S):
        kind, docid, body = m.group(1), m.group(2), m.group(3)
        entry = index.get(docid)
        if entry is None:
            entry = {"docid": docid, "short": "", "long": "", "no": numbers.get(docid, "")}
            index[docid] = entry
            results.append(entry)
        entry["short" if kind == "short" else "long"] = strip_tags(body)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("word", nargs="?", default="", help="คำค้น (หลายคำ = AND)")
    ap.add_argument("--section", default="", help="เลขมาตรา")
    ap.add_argument("--deka-no", default="", help="เลขฎีกา เช่น 485/2567")
    ap.add_argument("--year", nargs=2, metavar=("จาก", "ถึง"), help="ช่วงปี พ.ศ.")
    ap.add_argument("--full", action="store_true", help="ขอฉบับเต็ม + พิมพ์คำวินิจฉัยเต็ม")
    ap.add_argument("-n", "--num", type=int, default=5, help="จำนวนผลที่พิมพ์ (default 5)")
    ap.add_argument("--skip-control", action="store_true", help="ข้ามการตรวจ session-replay")
    args = ap.parse_args()

    if not (args.word or args.section or args.deka_no):
        ap.error("ต้องระบุคำค้น หรือ --section หรือ --deka-no")

    year_from, year_to = (args.year or ("", ""))
    with tempfile.TemporaryDirectory() as tmp:
        jar = Path(tmp) / "cookies.txt"
        fields = build_fields(word=args.word, section=args.section, deka_no=args.deka_no,
                              year_from=year_from, year_to=year_to, full=args.full)
        results = parse(query(fields, jar))

        # กับดัก: ส่ง params ผิดแล้วเซิร์ฟเวอร์คืนผลเดิมใน session แทนที่จะ error
        # → ยิงคำที่ไม่เกี่ยวกันเทียบ ถ้าได้ชุดเดียวกันแปลว่าผลไม่น่าเชื่อถือ
        if results and not args.skip_control:
            control = parse(query(build_fields(word=CONTROL_QUERY), jar))
            if control and {r["docid"] for r in control} == {r["docid"] for r in results}:
                print("⚠ ผลค้นเหมือน control query เป๊ะ = เซิร์ฟเวอร์คืนผลค้างใน session "
                      "ไม่ใช่ผลจริง — อย่านำไปอ้าง", file=sys.stderr)
                return 2

    if not results:
        print("ไม่พบคำพิพากษาที่ตรงกับคำค้น — รายงานว่า \"ไม่พบ\" ห้ามแต่งเลขฎีกา")
        return 1

    print(f"พบ {len(results)} รายการ (แสดง {min(args.num, len(results))})\n")
    for entry in results[:args.num]:
        title = f"คำพิพากษาศาลฎีกาที่ {entry['no']}" if entry["no"] else f"docid {entry['docid']}"
        print(f"=== {title}")
        body = entry["long"] if (args.full and entry["long"]) else (entry["short"] or entry["long"])
        print(body if args.full else body[:400] + ("…" if len(body) > 400 else ""))
        print()
    print("อ้างอิงรูปแบบ: คำพิพากษาศาลฎีกาที่ X/YYYY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
