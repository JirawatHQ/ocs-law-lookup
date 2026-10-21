#!/usr/bin/env python3
"""ดึงตัวบทกฎหมายเต็มฉบับ (รายมาตรา) จาก ocs.go.th → Markdown

ใช้กับ "ประมวลกฎหมาย" ที่ไม่มี PDF ใน list_table_search (อาญา/แพ่ง/วิ.อาญา ฯลฯ)
และกับ พ.ร.บ. ที่ต้องการตัวบท structured แทน PDF

  python3 ocs_getdoc.py <timelineId> [-o out.md]
  python3 ocs_getdoc.py --name penal -o corpus/local/penal_code.md   # ดึงฉบับล่าสุดเก็บในเครื่อง
  (--name: penal / crimproc / police — หา id ล่าสุดจาก ocs ทุกครั้ง ใช้ id ที่จดไว้เมื่อหาไม่เจอ)

เก็บไฟล์ที่ดึงเองใน corpus/local/ เสมอ อย่าเขียนทับไฟล์ใน corpus/ ที่มากับสกิล
(เขียนทับแล้ว git pull รอบหน้าจะไม่ยอมอัปเดต)
  python3 ocs_getdoc.py <timelineId> --json raw.json   # เก็บ JSON ดิบด้วย
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import HttpError, post_json  # noqa: E402
from _text import fix_console, law_key  # noqa: E402

fix_console()

API = "https://searchlaw.ocs.go.th/ocs-api/public/doc/getLawDoc"
OK_CODES = {"", "0", "000000", "SUCCESS", "None"}

# timelineId ที่ยืนยันแล้ว 2026-10-21 (ดู references/law_ids.md — วิธีหา id ของฉบับอื่นอยู่ในนั้น)
# ใช้เป็นทางสำรอง: --name จะค้นชื่อเต็มใน ocs ก่อน เผื่อ id เปลี่ยนเมื่อกฎหมายแก้ไข
KNOWN = {
    "penal": ("K2dTMURyaDllOXJVWVZqZGJLK09pdz09", "ประมวลกฎหมายอาญา"),
    "crimproc": ("UVdzUTNzUFZlT3VBOEw2allVWTZxZz09", "ประมวลกฎหมายวิธีพิจารณาความอาญา"),
    "police": ("UEY5OTdqYWRyZE9IM1NqTE5ZLzk4dz09", "พระราชบัญญัติตำรวจแห่งชาติ พ.ศ. 2565"),
}


def latest_id(name: str) -> str | None:
    """ค้นชื่อเต็มใน ocs คืน encTimelineID ของฉบับที่ชื่อตรงเป๊ะ (ไม่เจอ = None)"""
    from ocs_search import search
    try:
        res = search(name, content=0, perpage=20)
    except HttpError:
        return None
    for row in res.get("data") or []:
        title = re.sub(r"<[^>]+>", "", row.get("lawNameTh", ""))
        if law_key(title) == law_key(name) and row.get("encTimelineID"):
            return row["encTimelineID"]
    return None


def fetch(timeline_id: str, timeout: int = 60, retries: int = 3) -> dict:
    """ยิง getLawDoc — reqHeader เป็นค่า dummy ได้ แต่ต้องมีครบทุก key ไม่งั้น validate ตก

    เซิร์ฟเวอร์คืน PDL_CIPHER_EXCEPTION เป็นครั้งคราวเมื่อยิงติดกันเร็ว ๆ (ยิงซ้ำแล้วผ่าน)
    → retry พร้อมเว้นจังหวะ ไม่ใช่ error จริง
    """
    payload = {
        "reqHeader": {
            "reqId": "1",
            "reqChannel": "WEB",
            "reqDtm": "2026-01-01 00:00:00.000",
            "reqBy": "unknow",
            "serviceName": "getPublicLawDoc",
            "uuid": "x",
            "sessionId": "x",
        },
        "reqBody": {"isTransEng": False, "timelineId": timeline_id},
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://searchlaw.ocs.go.th/council-of-state/",
    }
    last_err = ""
    for attempt in range(retries):
        if attempt:
            time.sleep(2 * attempt)
        doc = post_json(API, json_body=payload, headers=headers, timeout=timeout)
        code = str(doc.get("respHeader", {}).get("errorCode", ""))
        if code in OK_CODES and isinstance(doc.get("respBody"), dict):
            return doc
        if code in OK_CODES:
            code = "ไม่มี respBody (รูปแบบคำตอบของ ocs อาจเปลี่ยน)"
        last_err = f"{code}: {doc.get('respHeader', {}).get('errorDesc', '')}"
    raise HttpError(f"getLawDoc ล้มเหลวหลังลอง {retries} ครั้ง — {last_err}")


def strip_html(raw: str) -> str:
    """sectionContent เป็น HTML ที่มี inline style เยอะ — เอาแต่ข้อความ"""
    text = re.sub(r"</p\s*>|<br\s*/?>", "\n", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


# sectionTypeId ที่ ocs ใช้ — ห้ามเดาจาก sectionNo อย่างเดียว เพราะ ภาค/ลักษณะ/หมวด/ส่วน
# ก็มี sectionNo ของตัวเอง (หมวด 3 จะกลายเป็น "มาตรา 3" ถ้าไม่ดู type)
TYPE_SECTION = "4"          # มาตรา
TYPE_TITLE = "1"            # ชื่อกฎหมาย (โผล่ซ้ำเมื่อขึ้นเอกสารใหม่ในไฟล์เดียว)
TYPE_TOC = "16"             # สารบาญ — ตัดทิ้ง (ตารางยุบเป็นข้อความอ่านไม่รู้เรื่อง)
TYPE_STRUCTURE = {"6": "ภาค", "7": "ลักษณะ", "8": "หมวด", "9": "ส่วน"}


def to_markdown(doc: dict) -> str:
    body = doc["respBody"]
    info = body.get("lawInfo", {})
    sections = body.get("lawSections", [])
    footnotes = body.get("footnoteList", [])
    n_sections = sum(1 for s in sections if s.get("sectionTypeId") == TYPE_SECTION)

    out = [
        f"# {info.get('lawNameTh', '(ไม่ทราบชื่อ)')}",
        "",
        "> ตัวบทจริงจาก ocs.go.th (สำนักงานคณะกรรมการกฤษฎีกา) ผ่าน getLawDoc",
        f"> ดึงเมื่อ: {date.today().isoformat()}",
        f"> lawCode: `{info.get('lawCode', '-')}` · timelineId: `{info.get('timelineId', '-')}`",
        f"> ประกาศ: {info.get('publishDateAd', '-')} · ใช้บังคับ: {info.get('effectiveDateStartAd', '-')}",
        f"> {n_sections} มาตรา (จาก {len(sections)} section)",
        "",
        "---",
        "",
    ]

    # ไฟล์เดียวมีหลายเอกสาร: พ.ร.บ.ให้ใช้ประมวลฯ → ตัวประมวล → พ.ร.บ.แก้ไขเพิ่มเติมท้ายเล่ม (30+ ฉบับ)
    # แต่ละฉบับมีมาตรา 1,2,3 ของตัวเอง → ต้องกำกับที่ heading ไม่งั้นค้น "มาตรา 2" ได้ผิดฉบับ
    main_title = re.sub(r"\s+", "", info.get("lawNameTh", ""))
    doc_label = ""
    in_main = False       # อยู่ในตัวบทหลักหรือยัง (ไม่ใช่ พ.ร.บ.ให้ใช้ฯ / ฉบับแก้ไขท้ายเล่ม)
    seen_title = False

    for sec in sections:
        stype = str(sec.get("sectionTypeId", ""))
        if stype == TYPE_TOC:
            continue
        content = strip_html(sec.get("sectionContent", ""))
        if not content:
            continue

        no = sec.get("sectionNo") or ""
        label = sec.get("sectionLabel", "")

        if stype == TYPE_SECTION:
            head = f"## มาตรา {no}" if no else f"## {label}"
            if not in_main:
                head += f"  〔{doc_label}〕"   # มาตราของฉบับแก้ไข/ฉบับให้ใช้ ไม่ใช่ตัวประมวล
            out.append(head)
        elif stype in TYPE_STRUCTURE:
            # เจอ ภาค/ลักษณะ = เข้าตัวประมวลแล้ว (ป.วิ.อ. ไม่มี title section ของตัวเอง
            # มีแต่ของ พ.ร.บ.ให้ใช้ฯ นำหน้า — ถ้าไม่เช็คตรงนี้ทั้งฉบับจะโดนติดป้ายผิด)
            in_main = True
            # บรรทัดแรกของ content คือ "ภาค ๑" ที่ซ้ำกับ label — ชื่อจริงอยู่บรรทัดถัดไป
            lines = [ln for ln in content.splitlines() if ln.strip()]
            name = lines[1] if len(lines) > 1 else ""
            out.append(f"### 〔{TYPE_STRUCTURE[stype]} {no}〕 {name}".rstrip())
            out.append("")
            continue
        elif stype == TYPE_TITLE:
            # เอกสารใหม่เริ่มตรงนี้ (เช่น พ.ร.บ.ให้ใช้ประมวลฯ จบ → ตัวประมวลเริ่มมาตรา 1 ใหม่)
            doc_label = re.sub(r"\s+", " ", content.replace("\n", " ")).strip()
            # ตัวบทหลักเริ่มเมื่อ title ตรงกับชื่อกฎหมาย (ป.อาญา) — ฉบับแก้ไขท้ายเล่มปิด flag นี้
            in_main = re.sub(r"\s+", "", doc_label) == main_title
            if seen_title:
                out += ["", "---", ""]
            seen_title = True
            out.append(f"# {doc_label}")
            out.append("")
            continue
        else:
            out.append(f"## 〔{label}〕")

        out.append("")
        out.append(content)
        out.append("")

    if footnotes:
        out += ["---", "", "## เชิงอรรถ (ที่มาการแก้ไข)", ""]
        for fn in footnotes:
            detect = fn.get("footnoteDetect", "")
            out.append(f"- [{detect}] {strip_html(fn.get('footnoteContent', ''))}")

    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("timeline_id", nargs="?", help="encTimelineID จาก ocs")
    ap.add_argument("--name", choices=sorted(KNOWN), help="penal / crimproc / police (หา id ล่าสุดจาก ocs ให้)")
    ap.add_argument("-o", "--out", help="ไฟล์ Markdown ปลายทาง (ไม่ใส่ = พิมพ์ออก stdout)")
    ap.add_argument("--json", dest="json_out", help="เก็บ JSON ดิบไว้ด้วย")
    args = ap.parse_args()

    if args.name:
        known_id, label = KNOWN[args.name]
        timeline_id = latest_id(label)
        if timeline_id is None:
            print(f"หา id ล่าสุดของ {label} จาก ocs ไม่เจอ — ใช้ id ที่จดไว้แทน", file=sys.stderr)
            timeline_id = known_id
        elif timeline_id != known_id:
            print(f"ocs มี id ใหม่ของ {label} (ต่างจากที่จดไว้) — ใช้ id ใหม่", file=sys.stderr)
    elif args.timeline_id:
        timeline_id, label = args.timeline_id, args.timeline_id
    else:
        ap.error("ต้องระบุ timeline_id หรือ --name")

    try:
        doc = fetch(timeline_id)
    except HttpError as exc:
        print(f"ดึงตัวบทไม่สำเร็จ: {exc}", file=sys.stderr)
        return 1

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)

    md = to_markdown(doc)
    n_sections = len(re.findall(r"^## มาตรา ", md, re.M))
    if n_sections == 0:
        print("ได้ตัวบท 0 มาตรา (คำตอบจาก ocs ผิดรูป) — ไม่เขียนไฟล์ ลองใหม่ภายหลัง", file=sys.stderr)
        return 1
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            old = len(re.findall(r"^## มาตรา ", out.read_text(encoding="utf-8"), re.M))
            if n_sections < old * 0.8:
                print(f"ได้ {n_sections} มาตรา น้อยกว่าไฟล์เดิม ({old}) มาก — ไม่เขียนทับ "
                      "(อาจดึงมาไม่ครบ) ถ้าแน่ใจให้ลบไฟล์เดิมก่อน", file=sys.stderr)
                return 1
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(md, encoding="utf-8")
        tmp.replace(out)              # เขียนเสร็จค่อยสลับ — ไฟล์เดิมไม่พังถ้าหลุดกลางทาง
        print(f"เขียน {out} ({n_sections} มาตรา, {len(md):,} ตัวอักษร) — {label}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
