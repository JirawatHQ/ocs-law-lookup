#!/usr/bin/env python3
"""ตรวจว่าสกิลพร้อมใช้ไหม — ใช้ไม่ได้เมื่อไหร่ ให้รันตัวนี้แล้วส่งผลทั้งหมดให้คนดูแล

  python3 scripts/selfcheck.py              ตรวจครบ (ยิง ocs กับเว็บศาลอย่างละ 1 ครั้ง)
  python3 scripts/selfcheck.py --offline    ตรวจเฉพาะในเครื่อง

ไม่แก้อะไรในเครื่อง แค่อ่านแล้วรายงาน · รหัสจบ 0 = ผ่านหมด, 1 = มีข้อไม่ผ่าน
"""
from __future__ import annotations

import argparse
import gzip
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _text import fix_console, law_key  # noqa: E402

fix_console()

ROOT = Path(__file__).resolve().parent.parent
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'ผ่าน' if ok else 'ไม่ผ่าน'}] {name}" + (f" — {detail}" if detail else ""))


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=cwd, timeout=30)
        return p.returncode, (p.stdout or p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, str(exc)


def check_machine() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "?"
    print(f"ocs-law-lookup {version} · Python {platform.python_version()} · "
          f"{platform.system()} {platform.release()} · {ROOT}\n")
    check("Python 3.9 ขึ้นไป", sys.version_info >= (3, 9), platform.python_version())
    curl = shutil.which("curl")
    rc, out = run([curl, "--version"]) if curl else (-1, "")
    check("มีคำสั่ง curl", rc == 0, out.splitlines()[0][:60] if rc == 0 else "ไม่พบ — ลง curl ก่อน")


def check_git() -> None:
    if not (ROOT / ".git").exists():
        check("ติดตั้งจาก git clone", False,
              "โฟลเดอร์นี้ไม่ได้มาจาก git clone (git pull ใช้ไม่ได้) — ดู README หัวข้อ 'เคยติดตั้งแบบ zip'")
        return
    if not shutil.which("git"):
        check("มีคำสั่ง git", False, "ไม่พบ git — อัปเดตด้วย git pull ไม่ได้")
        return
    rc, out = run(["git", "status", "--porcelain"], cwd=ROOT)
    changed = [ln for ln in out.splitlines() if ln.strip()] if rc == 0 else []
    check("ไม่มีไฟล์ของสกิลถูกแก้ (git pull ได้)", rc == 0 and not changed,
          "; ".join(changed[:5]) + (" … ดู README หัวข้อ 'ห้ามแก้ไฟล์ในโฟลเดอร์สกิล'" if changed else ""))
    rc, out = run(["git", "log", "-1", "--format=%h %cs"], cwd=ROOT)
    if rc == 0:
        print(f"       รุ่นในเครื่อง: {out}")


def check_corpus() -> None:
    files = sorted((ROOT / "corpus").glob("*.md"))
    local = sorted((ROOT / "corpus" / "local").glob("*.md")) if (ROOT / "corpus" / "local").is_dir() else []
    check("มีตัวบทในเครื่อง", bool(files), f"{len(files)} ฉบับ + ของเพิ่มเอง {len(local)} ฉบับใน corpus/local")
    for path in files + local:
        text = path.read_text(encoding="utf-8")
        n = len(re.findall(r"^## มาตรา ", text, re.M))
        fetched = re.search(r"ดึงเมื่อ:\s*(\S+)", text[:1500])
        where = "local/" if path.parent.name == "local" else ""
        print(f"       {where}{path.stem}: {n} มาตรา · ดึงเมื่อ {fetched.group(1) if fetched else 'ไม่ทราบ'}")
    # ไฟล์ใน local ที่ชื่อไฟล์ตรงกับของสกิล = ตั้งใจใช้แทน ไม่นับซ้ำ
    replaced = {p.stem for p in local}
    titles: dict[str, list[str]] = {}
    for path in [f for f in files if f.stem not in replaced] + local:
        first = path.read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ")
        titles.setdefault(law_key(first), []).append(f"{path.parent.name}/{path.name}")
    dup = [names for names in titles.values() if len(names) > 1]
    check("ไม่มีกฎหมายฉบับเดียวกันซ้ำสองไฟล์", not dup,
          "; ".join(" = ".join(n) for n in dup[:3]) + (" — ลบไฟล์ที่ซ้ำใน corpus/local" if dup else ""))


def check_index() -> None:
    path = ROOT / "corpus" / "deka_cite_index.json.gz"
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            data = json.load(fh)
        check("ดัชนีฎีกาอ่านได้", bool(data.get("cases")), f"{len(data['cases']):,} เลขฎีกา")
    except (OSError, ValueError, KeyError) as exc:
        check("ดัชนีฎีกาอ่านได้", False, str(exc)[:80])


def check_online() -> None:
    from _http import HttpError
    from ocs_search import search
    try:
        res = search("ประมวลกฎหมายอาญา", content=0, perpage=1)
        ok = isinstance(res.get("data"), list) and bool(res["data"])
        check("ต่อ ocs.go.th ได้", ok, "ค้นได้" if ok else "ได้คำตอบแต่อ่านไม่ออก")
    except HttpError as exc:
        check("ต่อ ocs.go.th ได้", False, str(exc)[:120])

    import deka_search
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as tmp:
            # แค่เปิดหน้าแรก ไม่ใช่การค้น (เว็บศาลห้ามยิงถี่)
            page = deka_search._curl(["-c", str(Path(tmp) / "c.txt"), f"{deka_search.BASE}/"], timeout=60)
        check("ต่อเว็บศาลฎีกาได้", "count_all_result" in page or "ฎีกา" in page,
              "เปิดหน้าแรกได้" if page else "ได้หน้าว่าง")
    except deka_search.DekaError as exc:
        check("ต่อเว็บศาลฎีกาได้", False, str(exc)[:120])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="ไม่ต่อเน็ต")
    args = ap.parse_args()

    check_machine()
    check_git()
    check_corpus()
    check_index()
    if not args.offline:
        check_online()

    failed = [name for name, ok, _ in results if not ok]
    print(f"\nผ่าน {len(results) - len(failed)}/{len(results)} ข้อ"
          + (f" · ไม่ผ่าน: {', '.join(failed)}" if failed else " · พร้อมใช้"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
