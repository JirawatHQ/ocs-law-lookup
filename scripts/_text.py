"""จัดรูปข้อความภาษาไทยให้ค้นเจอ — ใช้ร่วมกันทุกสคริปต์

ทำไมต้องมี: เลขมาตราเดียวกันเขียนได้หลายแบบ ("๓๔๑", "ม.341", "340ตรี", "321.", "3 (1)")
ถ้าแต่ละสคริปต์จัดรูปไม่เหมือนกัน ฝั่งหนึ่งค้นเจออีกฝั่งบอก "ไม่พบ" ทั้งที่มีข้อมูลอยู่
"""
from __future__ import annotations

import re
import sys

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

# คำต่อท้ายเลขมาตรา เรียงยาวก่อนสั้น (ไม่งั้น "อัฏฐ" กิน "อัฏฐารส" ครึ่งคำ)
SUFFIXES = ("อัฏฐารส", "สัตตรส", "โสฬส", "ปัณรส", "จตุทศ", "เตรส", "ทวาทศ", "เอกาทศ",
            "ทศ", "นว", "อัฏฐ", "สัตต", "เบญจ", "จัตวา", "ตรี", "ทวิ", "ฉ")
_SUFFIX_RE = "|".join(SUFFIXES)


def fix_console() -> None:
    """Windows: console เริ่มต้นเป็น cp874 → print ภาษาไทยแล้ว UnicodeEncodeError ทันที
    (macOS/Linux เป็น UTF-8 อยู่แล้ว เรียกแล้วไม่มีผล)"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def to_arabic(text: str) -> str:
    return text.translate(THAI_DIGITS)


def norm_thai(text: str) -> str:
    """สระอำแบบแยกส่วน (◌ํ + า) → ำ และยุบช่องว่าง

    PDF/เว็บราชการบางแห่งเก็บ "กำ" เป็น ก+U+0E4D+U+0E32 หน้าตาเหมือนกันแต่คนละไบต์
    unicodedata.normalize แก้ไม่ได้ ต้องแทนเอง
    """
    text = text.replace("ํา", "ำ")
    return re.sub(r"\s+", " ", text).strip()


def norm_section(raw: str) -> list[str]:
    """'ม.๓๔๑ (1)' → ['341'] · '340ตรี' → ['340 ตรี'] · '7, 224' → ['7', '224']

    ตัดอนุมาตรา/วรรค ทิ้ง (ค้น 341 ต้องเจอฎีกาที่อ้าง 341 (1) ด้วย)
    ช่วงเลข '249-60' เก็บไว้ตามเดิม เพราะตีความแน่ไม่ได้ว่าครอบมาตราไหนบ้าง
    """
    text = to_arabic(norm_thai(raw))
    out: list[str] = []
    for part in re.split(r"\s*(?:,|และ)\s*", text):
        part = re.sub(r"(มาตรา|ม\.)\s*", "", part)
        part = re.sub(r"\s*วรรค.*$", "", part)
        part = re.sub(r"\s*\(.*$", "", part)
        part = re.sub(r"\s*(เดิม|ใหม่)\s*$", "", part)
        part = part.strip(" .;:")
        part = re.sub(rf"(\d)\s*({_SUFFIX_RE})", r"\1 \2", part)
        part = re.sub(r"\s*-\s*", "-", part)            # '249 - 60' = '249-60'
        part = re.sub(r"\s+", " ", part).strip()
        if part and part != "-":
            out.append(part)
    return out


def canon_law(name: str) -> str:
    """ชื่อกฎหมายที่ต่างกันแค่ช่องว่าง ให้เป็นตัวเดียวกัน
    'พ.ร.ก. การกู้ยืมเงิน… พ.ศ. 2527' → 'พ.ร.ก.การกู้ยืมเงิน… พ.ศ.2527'"""
    name = to_arabic(norm_thai(name))
    return re.sub(r"\.\s+(?=\S)", ".", name)


def law_key(name: str) -> str:
    """ใช้เทียบชื่อกฎหมาย: ไม่สนช่องว่างเลย"""
    return re.sub(r"\s+", "", canon_law(name))
