"""รัน (ในโฟลเดอร์สกิล): python3 -m pytest tests -q

ใช้ข้อมูลสังเคราะห์ทั้งหมด ไม่มีเนื้อคำพิพากษาจริง (ลิขสิทธิ์ศาล)
ถ้ามีไฟล์ผลค้นจริงจากเว็บศาล ชี้ด้วย DEKA_FIXTURE=<path> เพื่อเทียบดัชนีกับหน้าเว็บจริงเพิ่ม
"""
import gzip
import json
import os
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import build_deka_index  # noqa: E402
import deka_cite  # noqa: E402
import deka_search  # noqa: E402
import law_grep  # noqa: E402
import ocs_getdoc  # noqa: E402
from _text import canon_law, law_key, norm_section  # noqa: E402


# ---- จัดรูปเลขมาตรา: ทุกแบบที่เจอจริงในข้อมูล ----

@pytest.mark.parametrize("raw, want", [
    ("๓๔๑", ["341"]),
    ("ม.341", ["341"]),
    ("มาตรา ๓๔๑", ["341"]),
    ("340ตรี", ["340 ตรี"]),
    ("336  ทวิ", ["336 ทวิ"]),
    ("321.", ["321"]),
    ("3 (1)", ["3"]),
    ("33(1)", ["33"]),
    ("176 วรรคหนึ่ง", ["176"]),
    ("7, 224", ["7", "224"]),
    ("334 เดิม", ["334"]),
    ("249 - 60", ["249-60"]),
    ("160 ทวิ/1", ["160 ทวิ/1"]),
    ("269/5", ["269/5"]),
    ("12 อัฏฐารส", ["12 อัฏฐารส"]),
    ("-", []),
])
def test_norm_section(raw, want):
    assert norm_section(raw) == want


def test_law_names_differing_only_by_space_are_same():
    assert law_key("พ.ร.ก. การกู้ยืมเงิน พ.ศ. 2527") == law_key("พ.ร.ก.การกู้ยืมเงิน พ.ศ.2527")
    assert canon_law("การชําระบัญชี") == "การชำระบัญชี"      # สระอำแยกส่วน


# ---- สร้างดัชนี ----

def test_build_normalizes_and_drops_bad_rows(tmp_path):
    rows = [
        {"case_id": "๑๐/๒๕๖๗", "sections_cited": ["ป.อ. มาตรา ๓๔๑", "ป.อ. มาตรา 340ตรี", "ป.อ. มาตรา 7, 224"]},
        {"case_id": "9/2567", "sections_cited": ["ป.อ. มาตรา 321."]},
        {"case_id": "716685", "sections_cited": ["ป.อ. มาตรา 1"]},          # เลขเอกสารภายใน
        {"case_id": "1549/1549", "sections_cited": ["ป.อ. มาตรา 1"]},       # ปีเสีย
        {"case_id": "5/2566", "sections_cited": ["พ.ร.ก. การกู้ มาตรา 4", "พ.ร.ก.การกู้ มาตรา 5"]},
    ]
    src = tmp_path / "c.jsonl"
    src.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    data = build_deka_index.build(src)
    assert data["meta"]["cases"] == 3 and data["meta"]["skipped_no_case_number"] == 2
    laws = data["laws"]
    assert len(laws) == 2                                  # พ.ร.ก. 2 แบบรวมเป็นฉบับเดียว
    secs = {c: {deka_cite.label(laws, s) for s in ss} for c, _, ss in data["cases"]}
    assert secs["10/2567"] == {"ป.อ. ม.341", "ป.อ. ม.340 ตรี", "ป.อ. ม.7", "ป.อ. ม.224"}
    assert secs["9/2567"] == {"ป.อ. ม.321"}


# ---- ค้นดัชนี ----

FAKE = {
    "laws": ["ป.อ.", "ป.วิ.อ.", "พ.ร.บ.ว่าด้วยการกระทำความผิดเกี่ยวกับคอมพิวเตอร์ พ.ศ.2550"],
    "cases": [
        ["9/2567", 2567, ["0:341", "0:343"]],
        ["10/2567", 2567, ["0:341", "0:343", "2:14"]],
        ["3/2568", 2568, ["0:341"]],
        ["4/2560", 2560, ["1:87"]],
    ],
}


def test_law_aliases_full_names():
    assert deka_cite.law_ids(FAKE["laws"], "ประมวลกฎหมายอาญา") == [0]
    assert deka_cite.law_ids(FAKE["laws"], "ป.วิ.อาญา") == [1]
    assert deka_cite.law_ids(FAKE["laws"], "คอมพิวเตอร์") == [2]
    assert deka_cite.law_ids(FAKE["laws"], "ไม่มีกฎหมายนี้") == []


def test_with_intersection_and_order():
    both = deka_cite.cases_citing(FAKE, [0], "341") & deka_cite.cases_citing(FAKE, [0], "343")
    assert both == {"9/2567", "10/2567"}
    by_case = {c: y for c, y, _ in FAKE["cases"]}
    rows = sorted(both, key=lambda c: (by_case[c], int(c.split("/")[0])), reverse=True)
    assert rows == ["10/2567", "9/2567"]                  # 10 มาก่อน 9 (เทียบเป็นตัวเลข ไม่ใช่ตัวอักษร)


def test_shipped_index_known_case():
    data = deka_cite.load()
    by_case = {c: secs for c, _, secs in data["cases"]}
    got = {deka_cite.label(data["laws"], s) for s in by_case["4920/2567"]}
    assert got == {"ป.อ. ม.342", "ป.อ. ม.343", "ป.อ. ม.83", "ป.อ. ม.86"}


# ---- อ่านหน้าเว็บศาล (HTML สังเคราะห์) ----

def _item(docid, no, short, long=None):
    html = (f'<input id="text_bookmark_name_{docid}" value="คำพิพากษาศาลฎีกาที่ {no}">'
            f'<li id="short_text_docid_{docid}">{short}</li>')
    if long is not None:
        html += f'<li id="long_text_docid_{docid}">{long}</li>'
    return html


def test_parse_pairs_by_docid_not_order():
    # bookmark ทั้งหมดมาก่อน แล้วบล็อกเนื้อหามาสลับลำดับ — ต้องผูกด้วย docid
    page = ('<input id="text_bookmark_name_2" value="คำพิพากษาศาลฎีกาที่ 2/2567">'
            '<input id="text_bookmark_name_1" value="คำพิพากษาศาลฎีกาที่ 1/2567">'
            '<li id="short_text_docid_1">ย่อหนึ่ง</li><li id="short_text_docid_2">ย่อสอง</li>'
            '<li id="long_text_docid_1">เต็มหนึ่ง</li>')
    got = {r["no"]: r for r in deka_search.parse(page)}
    assert got["1/2567"]["short"] == "ย่อหนึ่ง" and got["1/2567"]["long"] == "เต็มหนึ่ง"
    assert got["2/2567"]["short"] == "ย่อสอง" and got["2/2567"]["long"] == ""


def test_site_total_and_no_result_detection():
    assert deka_search.site_total("<p>พบ 1,234 คำพิพากษาศาลฎีกา จากทั้งหมด</p>") == 1234
    assert deka_search.looks_like_no_result("<p>พบ 0 คำพิพากษาศาลฎีกา</p>")
    # หน้าปิดปรับปรุง/หน้าตาเปลี่ยน ต้องไม่ถูกนับว่า "ไม่พบ"
    assert not deka_search.looks_like_no_result("<h1>ปิดปรับปรุงระบบ</h1>")
    # "ไม่พบ" ในเนื้อคำพิพากษาไม่ใช่สัญญาณว่าไม่มีผล
    assert not deka_search.looks_like_no_result(_item(1, "1/2567", "จำเลยที่ 2 ไม่พบประวัติการเดินทาง"))


def test_layout_change_exits_4_not_not_found(monkeypatch, capsys):
    monkeypatch.setattr(deka_search, "query", lambda fields, jar, retries=0, path="/search": "<h1>ระบบใหม่</h1>")
    monkeypatch.setattr(sys, "argv", ["deka_search.py", "ฉ้อโกง", "--skip-control"])
    assert deka_search.main() == 4
    assert "อ่านผลจากหน้าเว็บศาลไม่ออก" in capsys.readouterr().err


def test_network_error_exits_3(monkeypatch, capsys):
    def boom(fields, jar, retries=0, path="/search"):
        raise deka_search.DekaError("เว็บศาลตัดการเชื่อมต่อ")
    monkeypatch.setattr(deka_search, "query", boom)
    monkeypatch.setattr(sys, "argv", ["deka_search.py", "ฉ้อโกง"])
    assert deka_search.main() == 3
    assert "ไม่ได้แปลว่าไม่มีฎีกา" in capsys.readouterr().err


def test_full_without_long_is_labelled(monkeypatch, capsys):
    page = "<p>พบ 1 คำพิพากษาศาลฎีกา</p>" + _item(7, "7/2566", "ข้อความย่อ")
    monkeypatch.setattr(deka_search, "query", lambda fields, jar, retries=0, path="/search": page)
    monkeypatch.setattr(sys, "argv", ["deka_search.py", "x", "--full", "--skip-control"])
    assert deka_search.main() == 0
    assert "(ฉบับย่อ:" in capsys.readouterr().out


def test_reports_site_total_not_page_count(monkeypatch, capsys):
    page = "<p>พบ 63 คำพิพากษาศาลฎีกา</p>" + "".join(_item(i, f"{i}/2566", "ย่อ") for i in range(1, 21))
    monkeypatch.setattr(deka_search, "query", lambda fields, jar, retries=0, path="/search": page)
    monkeypatch.setattr(sys, "argv", ["deka_search.py", "x", "--skip-control"])
    deka_search.main()
    assert "ทั้งหมด 63 เรื่อง" in capsys.readouterr().out


# ---- ตัวบทในเครื่อง ----

CORPUS_MD = """# ประมวลกฎหมายอาญา

> ตัวบทจริงจาก ocs.go.th (สำนักงานคณะกรรมการกฤษฎีกา) ผ่าน getLawDoc
> ดึงเมื่อ: 2026-07-21
> ประกาศ: 1956-11-15 · ใช้บังคับ: 2025-12-30

### 〔ภาค 2〕 ความผิด
## มาตรา ๒๗๗ ทวิ

ข้อความ ๒๗๗ ทวิ

## มาตรา ๓๔๑

ข้อความ ๓๔๑

## มาตรา 2  〔พระราชบัญญัติแก้ไขเพิ่มเติม〕

ข้อความฉบับแก้ไข
"""


@pytest.fixture
def fake_corpus(tmp_path, monkeypatch):
    (tmp_path / "local").mkdir()
    (tmp_path / "penal_code.md").write_text(CORPUS_MD, encoding="utf-8")
    monkeypatch.setattr(law_grep, "CORPUS", tmp_path)
    monkeypatch.setattr(law_grep, "LOCAL", tmp_path / "local")
    return tmp_path


@pytest.mark.parametrize("q", ["341", "ม.341", "มาตรา ๓๔๑", "๓๔๑"])
def test_law_grep_section_forms(fake_corpus, capsys, q):
    assert law_grep.by_section(q, "") == 0
    out = capsys.readouterr().out
    assert "ข้อความ ๓๔๑" in out and "ดึงเมื่อ 2026-07-21" in out


def test_law_grep_suffix_glued(fake_corpus, capsys):
    assert law_grep.by_section("277ทวิ", "") == 0
    assert "ข้อความ ๒๗๗ ทวิ" in capsys.readouterr().out


def test_law_grep_local_overrides_shipped(fake_corpus, capsys):
    newer = CORPUS_MD.replace("2026-07-21", "2026-12-01").replace("ข้อความ ๓๔๑", "ข้อความใหม่ ๓๔๑")
    (fake_corpus / "local" / "penal_code.md").write_text(newer, encoding="utf-8")
    law_grep.by_section("341", "")
    out = capsys.readouterr().out
    assert "ข้อความใหม่ ๓๔๑" in out and "corpus/local" in out
    assert "ข้อความ ๓๔๑\n" not in out


# ---- แปลงตัวบทจาก ocs ----

def test_to_markdown_chapter_is_not_section_and_amendments_labelled():
    doc = {"respBody": {
        "lawInfo": {"lawNameTh": "ประมวลกฎหมายอาญา"},
        "lawSections": [
            {"sectionTypeId": "1", "sectionContent": "ประมวลกฎหมายอาญา"},
            {"sectionTypeId": "8", "sectionNo": "3", "sectionContent": "หมวด 3\nความผิดฐานฉ้อโกง"},
            {"sectionTypeId": "4", "sectionNo": "341", "sectionContent": "<p>ผู้ใดโดยทุจริต</p>"},
            {"sectionTypeId": "1", "sectionContent": "พระราชบัญญัติแก้ไขเพิ่มเติม (ฉบับที่ 30)"},
            {"sectionTypeId": "4", "sectionNo": "2", "sectionContent": "ให้ใช้บังคับ"},
        ],
    }}
    md = ocs_getdoc.to_markdown(doc)
    assert "## มาตรา 3\n" not in md and "### 〔หมวด 3〕 ความผิดฐานฉ้อโกง" in md
    assert "## มาตรา 341\n" in md
    assert "## มาตรา 2  〔พระราชบัญญัติแก้ไขเพิ่มเติม (ฉบับที่ 30)〕" in md
    assert re.search(r"> ดึงเมื่อ: \d{4}-\d{2}-\d{2}", md)


# ---- เทียบกับหน้าเว็บศาลจริง (เฉพาะเมื่อมีไฟล์) ----

FIXTURE = Path(os.environ.get("DEKA_FIXTURE", "/nonexistent"))


@pytest.mark.skipif(not FIXTURE.exists(), reason="ไม่ได้ชี้ DEKA_FIXTURE (ผลค้นจริงจากเว็บศาล ไม่แจกเพราะลิขสิทธิ์)")
def test_index_matches_official_search_page():
    """มาตราที่เว็บศาลแสดง ต้องอยู่ในดัชนีครบ (วัด 21 ต.ค. 69: 58/58)"""
    html = FIXTURE.read_text(encoding="utf-8")
    marks = [(m.start(), m.group(1)) for m in re.finditer(
        r'id="text_bookmark_name_\d+"[^>]*value="คำพิพากษาศาลฎีกาที่ ([^"]+)"', html)]
    data = deka_cite.load()
    by_case = {c: {deka_cite.label(data["laws"], s) for s in secs} for c, _, secs in data["cases"]}
    checked = 0
    for m in re.finditer(r"sectionView\('[^']*', '[^']*', '([^']*)', '([^']*)'", html):
        before = [case for pos, case in marks if pos < m.start()]
        if not before:
            continue
        sec = norm_section(m.group(2))[0]
        assert f"{m.group(1)} ม.{sec}" in by_case[before[-1]]
        checked += 1
    assert checked >= 50


# ---- ฟอร์มที่ส่งไปเว็บศาล (ยืนยันกับเว็บจริง 21 ต.ค. 69) ----

def test_deka_no_uses_basic_field():
    f = deka_search.build_fields(deka_no="3664/2568")
    assert f["search_deka_no"] == "3664/2568" and f["search_form_type"] == "basic"
    assert not any(k.startswith("adv_") for k in f)       # ฟิลด์ adv_* ได้ 0 ผลเงียบๆ


@pytest.mark.parametrize("name, code", [
    ("ป.อ.", "ป06-01"), ("ประมวลกฎหมายอาญา", "ป06-01"), ("ป.วิ.อาญา", "ป05-01"),
    ("คอมพิวเตอร์", "ฮ04-96"), ("ฟอกเงิน", "ฮ 1-25"), ("วิธีพิจารณา", None), ("ยาเสพติด", None),
])
def test_find_section_law(name, code):
    law = deka_search.find_section_law(name)
    assert (law[0] if law else None) == code


def test_section_search_posts_to_section_endpoint(monkeypatch):
    seen = {}

    def fake(fields, jar, retries=0, path="/search"):
        seen.update(fields, path=path)
        return '<input name="count_result" value="0">'
    monkeypatch.setattr(deka_search, "query", fake)
    monkeypatch.setattr(sys, "argv", ["deka_search.py", "--section", "ม.343", "--law", "ประมวลกฎหมายอาญา"])
    assert deka_search.main() == 1                        # count_result=0 = ไม่พบจริง
    assert seen["path"] == "/search/section" and seen["lawid"] == "ป06-01" and seen["section"] == "343"


def test_unsupported_section_law_is_explicit(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["deka_search.py", "--section", "15", "--law", "ยาเสพติด"])
    assert deka_search.main() == 2
    assert "ยังรองรับเฉพาะ" in capsys.readouterr().err


def test_to_markdown_title_with_thai_digits_is_main_act():
    """หัวเรื่อง "พ.ศ. ๒๕๓๙" ต้องนับเป็นตัวบทหลัก ไม่ใช่ฉบับแก้ไข (เคยติดป้ายผิด ม.1-5 พ.ร.บ.ตร.)"""
    doc = {"respBody": {
        "lawInfo": {"lawNameTh": "พระราชบัญญัติวิธีปฏิบัติราชการทางปกครอง พ.ศ. 2539"},
        "lawSections": [
            {"sectionTypeId": "1", "sectionContent": "พระราชบัญญัติ\nวิธีปฏิบัติราชการทางปกครอง\nพ.ศ. ๒๕๓๙"},
            {"sectionTypeId": "4", "sectionNo": "3", "sectionContent": "วิธีปฏิบัติราชการ"},
        ],
    }}
    assert "## มาตรา 3\n" in ocs_getdoc.to_markdown(doc)


def test_civil_code_book_is_top_of_breadcrumb(tmp_path, monkeypatch, capsys):
    doc = {"respBody": {
        "lawInfo": {"lawNameTh": "ประมวลกฎหมายแพ่งและพาณิชย์"},
        "lawSections": [
            {"sectionTypeId": "5", "sectionNo": "1", "sectionContent": "บรรพ ๑\nหลักทั่วไป"},
            {"sectionTypeId": "7", "sectionNo": "1", "sectionContent": "ลักษณะ ๑\nบทเบ็ดเสร็จทั่วไป"},
            {"sectionTypeId": "4", "sectionNo": "1", "sectionContent": "มาตรา ๑"},
            {"sectionTypeId": "5", "sectionNo": "2", "sectionContent": "บรรพ ๒\nหนี้"},
            {"sectionTypeId": "7", "sectionNo": "5", "sectionContent": "ลักษณะ ๕\nละเมิด"},
            {"sectionTypeId": "4", "sectionNo": "420", "sectionContent": "มาตรา ๔๒๐ ผู้ใดจงใจ"},
        ],
    }}
    (tmp_path / "civil_code.md").write_text(ocs_getdoc.to_markdown(doc), encoding="utf-8")
    monkeypatch.setattr(law_grep, "CORPUS", tmp_path)
    monkeypatch.setattr(law_grep, "LOCAL", tmp_path / "local")
    law_grep.by_section("420", "")
    assert "(บรรพ 2 หนี้ › ลักษณะ 5 ละเมิด)" in capsys.readouterr().out
