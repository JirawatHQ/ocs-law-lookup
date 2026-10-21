#!/usr/bin/env python3
"""ค้นคำพิพากษาศาลฎีกา จาก deka.supremecourt.or.th (ศาลฎีกา)

ocs.go.th ไม่มีฎีกา — คนละแหล่งกัน ตัวนี้ใช้เมื่อถามถึงแนวคำวินิจฉัย/บรรทัดฐาน

  python3 deka_search.py "ฉ้อโกงประชาชน"
  python3 deka_search.py "รับของโจร บัญชีเงินฝาก"    # หลายคำ = AND
  python3 deka_search.py --section 341               # ค้นตามมาตรา (ค่าตั้งต้น ป.อ.)
  python3 deka_search.py --section 14 --law คอมพิวเตอร์   # มาตราของกฎหมายอื่น
  python3 deka_search.py --deka-no 485/2567          # ค้นตามเลขฎีกา
  python3 deka_search.py "ฉ้อโกง" --full             # พิมพ์คำวินิจฉัยตัวเต็ม
  python3 deka_search.py "ฉ้อโกง" --year 2560 2569   # จำกัดช่วงปี พ.ศ.

ข้อควรระวัง:
- ค้นทีละเรื่องที่ใช้จริงในคดี ห้าม bulk-scrape (เว็บของศาลฎีกา มีเงื่อนไขการใช้เว็บ ไม่ยิงถี่)
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
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _text import fix_console, law_key, norm_section  # noqa: E402

fix_console()

BASE = "https://deka.supremecourt.or.th"
# คำที่ไม่เกี่ยวกับคำค้นจริง ใช้ตรวจว่าเซิร์ฟเวอร์ตอบตามที่ส่งไปจริง (ตัวที่สองไว้ใช้เมื่อผู้ใช้ค้นคำแรกเอง)
CONTROL_QUERIES = ("ลิขสิทธิ์", "ภาษีมูลค่าเพิ่ม")
TIMEOUT = 150      # วินาทีต่อครั้ง — บางคำค้นช้าเกิน 110 วิ จริง
RETRIES = 1        # ลองซ้ำอีก 1 ครั้ง: แย่สุด ~5 นาทีต่อคำค้น ไม่ใช่ค้างครึ่งชั่วโมง


# รหัสกฎหมายที่เว็บศาลใช้ค้นตามมาตรา (POST /search/section) — เก็บจาก sectionView(...) ในหน้าผลจริง
# (รหัส, ชื่อเต็ม, ชื่อย่อ) · ฉบับที่ไม่อยู่ในนี้: ใช้ deka_cite.py หรือค้นด้วยคำแทน
SECTION_LAWS = [
    ("ป06-01", "ประมวลกฎหมายอาญา", "ป.อ."),
    ("ป05-01", "ประมวลกฎหมายวิธีพิจารณาความอาญา", "ป.วิ.อ."),
    ("ป03-05", "ประมวลกฎหมายแพ่งและพาณิชย์", "ป.พ.พ."),
    ("ป04-01", "ประมวลกฎหมายวิธีพิจารณาความแพ่ง", "ป.วิ.พ."),
    ("ค84-01", "พระราชบัญญัติคุ้มครองผู้บริโภค พ.ศ.2522", "พ.ร.บ.คุ้มครองผู้บริโภค พ.ศ.2522"),
    ("ฮ04-96", "พระราชบัญญัติว่าด้วยการกระทำความผิดเกี่ยวกับคอมพิวเตอร์ พ.ศ.2550",
     "พ.ร.บ.ว่าด้วยการกระทำความผิดเกี่ยวกับคอมพิวเตอร์ พ.ศ.2550"),
    ("ฮ 1-25", "พระราชบัญญัติป้องกันและปราบปรามการฟอกเงิน พ.ศ.2542",
     "พ.ร.บ.ป้องกันและปราบปรามการฟอกเงิน พ.ศ.2542"),
    ("ฮ06-37", "พระราชบัญญัติป้องกันและปราบปรามการมีส่วนร่วมในองค์กรอาชญากรรมข้ามชาติ พ.ศ.2556",
     "พ.ร.บ.ป้องกันและปราบปรามการมีส่วนร่วมในองค์กรอาชญากรรมข้ามชาติ พ.ศ.2556"),
    ("ฮ02-63", "พระราชบัญญัติวิธีพิจารณาคดีผู้บริโภค พ.ศ.2551", "พ.ร.บ.วิธีพิจารณาคดีผู้บริโภค พ.ศ.2551"),
    ("ฮ07-13", "พระราชบัญญัติคุมประพฤติ พ.ศ.2559", "พ.ร.บ.คุมประพฤติ พ.ศ.2559"),
]
LAW_ALIASES = {"ป.อาญา": "ป.อ.", "ป.วิ.อาญา": "ป.วิ.อ.", "ป.วิ.แพ่ง": "ป.วิ.พ."}


def find_section_law(name: str) -> tuple[str, str, str] | None:
    """ชื่อเต็ม/ชื่อย่อ/บางส่วนของชื่อ → (รหัส, ชื่อเต็ม, ชื่อย่อ) ถ้าตรงได้ฉบับเดียว"""
    key = law_key(LAW_ALIASES.get(name.strip(), name))
    exact = [law for law in SECTION_LAWS if key in (law_key(law[1]), law_key(law[2]))]
    if exact:
        return exact[0]
    partial = [law for law in SECTION_LAWS if key in law_key(law[1])]
    return partial[0] if len(partial) == 1 else None


class DekaError(RuntimeError):
    """ติดต่อเว็บศาลไม่สำเร็จ — ไม่ได้แปลว่าไม่มีฎีกา"""
# ⚠ ไม่ส่ง User-Agent = เซิร์ฟเวอร์ไม่ตอบเลย (timeout/connection reset) ไม่ใช่เน็ตเสีย
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _curl(args: list[str], timeout: int = TIMEOUT) -> str:
    if not shutil.which("curl"):
        raise DekaError("ต้องมี curl ในเครื่อง (urllib โดน reset ที่ TLS handshake กับเว็บนี้)")
    # encoding="utf-8" จำเป็น: บน Windows text=True จะถอด HTML ด้วย cp874 → เนื้อคำพิพากษาเพี้ยน
    # แบบไม่ error (พังเงียบ — ได้ผลลัพธ์ผิดโดยไม่รู้ตัว)
    proc = subprocess.run(["curl", "-sS", "--max-time", str(timeout), "-H", f"User-Agent: {UA}", *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        reason = {28: "หมดเวลารอ (เว็บศาลช้ามาก)", 35: "เว็บศาลตัดการเชื่อมต่อ",
                  56: "เว็บศาลตัดการเชื่อมต่อ", 6: "หาเว็บศาลไม่เจอ (เน็ตหลุด?)",
                  7: "ต่อเว็บศาลไม่ได้"}.get(proc.returncode, f"curl รหัส {proc.returncode}")
        raise DekaError(f"{reason} — {proc.stderr.strip()[:120]}")
    return proc.stdout


def query(fields: dict, cookie_jar: Path, retries: int = RETRIES, path: str = "/search") -> str:
    """POST /search (หรือ /search/section) — ต้องมี session cookie ก่อน ไม่งั้นคืนผลค้างจาก session เดิม"""
    data = "&".join(f"{k}={v}" for k, v in _encode(fields).items())
    last = ""
    for attempt in range(retries + 1):
        if attempt:
            print(f"  ลองใหม่ครั้งที่ {attempt} ({last})", file=sys.stderr)
            time.sleep(10)
        try:
            if not cookie_jar.exists() or cookie_jar.stat().st_size == 0:
                _curl(["-c", str(cookie_jar), f"{BASE}/"], timeout=60)
            html_text = _curl(["-c", str(cookie_jar), "-b", str(cookie_jar),
                               "-X", "POST", f"{BASE}{path}", "--data", data,
                               "-H", "Content-Type: application/x-www-form-urlencoded"])
        except DekaError as exc:
            last = str(exc)
            continue
        if html_text.strip():
            return html_text
        last = "คำตอบว่าง (เซิร์ฟเวอร์ช้าหรือ timeout)"
    raise DekaError(last)


def _encode(fields: dict) -> dict:
    from urllib.parse import quote
    return {k: quote(str(v)) for k, v in fields.items()}


def section_fields(law: tuple[str, str, str], section: str) -> dict:
    """ฟอร์มที่ปุ่มมาตราในหน้าเว็บศาลส่ง (sectionView) — ไปที่ /search/section"""
    code, full_name, short_name = law
    return {"lawid": code, "lawfname": full_name, "lawsname": short_name, "section": section}


def build_fields(*, word: str = "", deka_no: str = "",
                 year_from: str = "", year_to: str = "", full: bool = False) -> dict:
    fields = {
        "search_doctype": 1,            # 1 = คำพิพากษาศาลฎีกา
        "search_type": 2 if full else 1,  # 1 = ฉบับย่อ, 2 = ฉบับเต็ม
        "start": "true",                # ⚠ ต้องเป็น true ไม่ใช่ตัวเลข ไม่งั้นได้ผลค้างใน session
        "search_form_type": "basic",
    }
    if word:
        fields["search_word"] = word
    if deka_no:
        # ฟอร์มพื้นฐานรับเลขฎีกาตรงๆ ที่ search_deka_no (ฟิลด์ adv_* ใช้ไม่ได้ ได้ 0 ผลเงียบๆ)
        fields["search_deka_no"] = deka_no
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


def site_total(html_text: str) -> int | None:
    """จำนวนที่เว็บศาลแจ้งว่าพบทั้งหมด (หน้าผลแสดงทีละ 20 เรื่อง)

    อ่านจาก <input name="count_result"> ก่อน (มีทั้งหน้าที่พบและไม่พบ) แล้วค่อยดูข้อความ "พบ N คำพิพากษา"
    """
    m = re.search(r'name="count_result"\s+value="(\d+)"', html_text)
    if m:
        return int(m.group(1))
    m = re.search(r"พบ\s*([\d,]+)\s*คำพิพากษา", strip_tags(html_text))
    return int(m.group(1).replace(",", "")) if m else None


def looks_like_no_result(html_text: str) -> bool:
    """หน้าแจ้งว่าไม่พบจริง (ต่างจากหน้าที่สคริปต์อ่านไม่ออก) — ดูเฉพาะข้อความที่มองเห็น"""
    visible = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html_text)
    # คำว่า "ไม่พบ" เฉยๆ ใช้ไม่ได้ — โผล่ในเนื้อคำพิพากษาเอง ("ไม่พบประวัติการเดินทาง…")
    return (site_total(visible) == 0
            or re.search(r"ไม่พบ(ข้อมูล|ผลการค้นหา|คำพิพากษา)", strip_tags(visible)) is not None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("word", nargs="?", default="", help="คำค้น (หลายคำ = AND)")
    ap.add_argument("--section", default="", help="เลขมาตรา (ใช้คู่ --law ค่าตั้งต้น ป.อ.)")
    ap.add_argument("--law", default="ป.อ.", help="กฎหมายของ --section (ชื่อเต็ม/ชื่อย่อ/บางส่วน)")
    ap.add_argument("--deka-no", default="", help="เลขฎีกา เช่น 485/2567")
    ap.add_argument("--year", nargs=2, metavar=("จาก", "ถึง"), help="ช่วงปี พ.ศ.")
    ap.add_argument("--full", action="store_true", help="ขอฉบับเต็ม + พิมพ์คำวินิจฉัยเต็ม")
    ap.add_argument("-n", "--num", type=int, default=5, help="จำนวนผลที่พิมพ์ (default 5)")
    ap.add_argument("--skip-control", action="store_true", help="ข้ามการตรวจ session-replay")
    args = ap.parse_args()

    if not (args.word or args.section or args.deka_no):
        ap.error("ต้องระบุคำค้น หรือ --section หรือ --deka-no")
    if args.section and (args.word or args.deka_no):
        ap.error("--section ใช้เดี่ยวๆ (เว็บศาลค้นตามมาตราแยกจากค้นคำ)")
    section_law = None
    if args.section:
        section_law = find_section_law(args.law)
        if section_law is None:
            names = ", ".join(law[2] for law in SECTION_LAWS)
            print(f"ค้นตามมาตราบนเว็บศาลยังรองรับเฉพาะ: {names}\n"
                  f"กฎหมายอื่นใช้ python3 scripts/deka_cite.py <มาตรา> --law \"{args.law}\" "
                  "หรือค้นด้วยคำแทน", file=sys.stderr)
            return 2
        sections = norm_section(args.section)
        if not sections:
            ap.error(f"อ่านเลขมาตราจาก '{args.section}' ไม่ออก")

    year_from, year_to = (args.year or ("", ""))
    print("กำลังค้นเว็บศาลฎีกา (ปกติ 1-2 นาที)…", file=sys.stderr)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            jar = Path(tmp) / "cookies.txt"
            if section_law:
                page = query(section_fields(section_law, sections[0]), jar, path="/search/section")
            else:
                fields = build_fields(word=args.word, deka_no=args.deka_no,
                                      year_from=year_from, year_to=year_to, full=args.full)
                page = query(fields, jar)
            results = parse(page)

            # กับดัก: ส่ง params ผิดแล้วเซิร์ฟเวอร์คืนผลเดิมใน session แทนที่จะ error
            # → ยิงคำที่ไม่เกี่ยวกันเทียบ ถ้าได้ชุดเดียวกันแปลว่าผลไม่น่าเชื่อถือ
            if results and not args.skip_control:
                control_word = next((w for w in CONTROL_QUERIES if w not in args.word), None)
                control = parse(query(build_fields(word=control_word), jar)) if control_word else []
                if control and {r["docid"] for r in control} == {r["docid"] for r in results}:
                    print("⚠ ผลค้นเหมือน control query เป๊ะ = เซิร์ฟเวอร์คืนผลค้างใน session "
                          "ไม่ใช่ผลจริง — อย่านำไปอ้าง", file=sys.stderr)
                    return 2
    except DekaError as exc:
        print(f"ติดต่อเว็บศาลไม่สำเร็จ: {exc}\n"
              "ไม่ได้แปลว่าไม่มีฎีกา — ลองใหม่ภายหลัง หรือค้นเองที่ https://deka.supremecourt.or.th",
              file=sys.stderr)
        return 3

    if not results:
        if looks_like_no_result(page):
            print("ไม่พบคำพิพากษาที่ตรงกับคำค้น — รายงานว่า \"ไม่พบ\" ห้ามแต่งเลขฎีกา")
            return 1
        print("อ่านผลจากหน้าเว็บศาลไม่ออก (รูปแบบหน้าเว็บอาจเปลี่ยน สคริปต์อาจต้องอัปเดต)\n"
              "ห้ามสรุปว่าไม่มีฎีกา — ค้นเองที่ https://deka.supremecourt.or.th", file=sys.stderr)
        return 4

    total = site_total(page)
    shown = min(args.num, len(results))
    if total and total > len(results):
        print(f"เว็บศาลแจ้งพบทั้งหมด {total:,} เรื่อง · หน้านี้ได้ {len(results)} · แสดง {shown}\n")
    else:
        print(f"พบ {len(results)} รายการ (แสดง {shown})\n")
    for entry in results[:args.num]:
        title = f"คำพิพากษาศาลฎีกาที่ {entry['no']}" if entry["no"] else f"docid {entry['docid']}"
        print(f"=== {title}")
        if args.full and entry["long"]:
            print(entry["long"])
        elif args.full:
            print("(ฉบับย่อ: เว็บศาลไม่ได้ส่งฉบับเต็มของเรื่องนี้มาในหน้าผล)")
            print(entry["short"])
        else:
            body = entry["short"] or entry["long"]
            print(body[:400] + ("…" if len(body) > 400 else ""))
        print()
    print("อ้างอิงรูปแบบ: คำพิพากษาศาลฎีกาที่ X/YYYY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
