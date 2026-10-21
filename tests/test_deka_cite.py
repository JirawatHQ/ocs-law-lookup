"""รัน: python3 -m pytest projects/skill-share/ocs-law-lookup/tests -q"""
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import deka_cite  # noqa: E402

FIXTURE = HERE.parent.parent / "fixtures" / "deka_search_chokong.html"


def test_norm_no_thai_digits_and_suffix():
    assert deka_cite.norm_no("๓๔๑") == "341"
    assert deka_cite.norm_no("มาตรา 277ทวิ") == "277 ทวิ"
    assert deka_cite.norm_no("ม. 336  ทวิ") == "336 ทวิ"


def test_base_no_drops_subsection_only():
    assert deka_cite.base_no("3 (1)") == "3"
    assert deka_cite.base_no("160 ทวิ/1") == "160 ทวิ/1"


def test_law_exact_name_wins():
    assert deka_cite.law_ids(["ป.อ.", "ป.อ.x"], "ป.อ.") == [0]
    assert deka_cite.law_ids(["พ.ร.บ.ก 2550", "พ.ร.บ.ก (ฉบับที่ 2)"], "พ.ร.บ.ก") == [0, 1]


def test_known_case_sections():
    data = deka_cite.load()
    by_case = {c: secs for c, _, secs in data["cases"]}
    got = {deka_cite.label(data["laws"], s) for s in by_case["4920/2567"]}
    assert got == {"ป.อ. ม.342", "ป.อ. ม.343", "ป.อ. ม.83", "ป.อ. ม.86"}


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture ผลค้นเว็บศาลไม่ได้แนบมา (ลิขสิทธิ์)")
def test_index_matches_official_search_page():
    """มาตราที่เว็บศาลแสดงใน 20 เรื่อง ต้องอยู่ในดัชนีครบ (วัด 21 ต.ค. 69: 58/58)"""
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
        assert f"{m.group(1)} ม.{m.group(2)}" in by_case[before[-1]]
        checked += 1
    assert checked >= 50
