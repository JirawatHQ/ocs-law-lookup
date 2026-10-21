# ocs-law-lookup — สกิลค้นกฎหมายไทยสำหรับ Claude Code

ให้ Claude ค้นตัวบทกฎหมายไทยและคำพิพากษาฎีกาจาก**แหล่งทางการ**ก่อนตอบ
แทนที่จะตอบมาตราจากความจำ (ซึ่งมักผิดและตรวจไม่ได้)

## ติดตั้ง

clone ลงโฟลเดอร์ skills ของ Claude Code ตรงๆ:

**macOS / Linux:**
```bash
git clone https://github.com/JirawatHQ/ocs-law-lookup.git ~/.claude/skills/ocs-law-lookup
```

**Windows** (PowerShell):
```powershell
git clone https://github.com/JirawatHQ/ocs-law-lookup.git "$env:USERPROFILE\.claude\skills\ocs-law-lookup"
```

อัปเดตรุ่นใหม่: `git -C ~/.claude/skills/ocs-law-lookup pull`

เปิด Claude Code ใหม่ พิมพ์ `/skills` ควรเห็น `ocs-law-lookup` ในรายการ

**ต้องมี:**
- **Python 3.9+** — Windows: ลงจาก python.org หรือ `winget install Python.Python.3.12`
  (ตอนติดตั้งติ๊ก "Add python.exe to PATH" ด้วย) · macOS มีมาแล้ว
- **curl** — Windows 10 build 1803+ / macOS มีมาแล้ว
- **git** — Windows: `winget install Git.Git` · macOS มีมาแล้ว (หรือลงผ่าน Xcode Command Line Tools)
- ไม่ต้องลง library เพิ่มเลย

> **Windows: คำสั่งใช้ `python` ไม่ใช่ `python3`** (บางเครื่องเป็น `py`)
> ตัวอย่างในเอกสารเขียน `python3` ให้เปลี่ยนเป็น `python` ทุกที่
> ภาษาไทยแสดงผลได้เลย ไม่ต้อง `chcp 65001` — สคริปต์บังคับ UTF-8 ให้แล้ว

## ใช้ยังไง

ไม่ต้องพิมพ์คำสั่งเอง — ถาม Claude เป็นภาษาคนได้เลย สกิลจะเด้งเอง:

- "ป.อ. มาตรา 343 ว่าอะไร"
- "ฉ้อโกงประชาชนมีฎีกาว่าไว้ยังไงบ้าง"
- "ฎีกาไหนอ้าง ป.อ. 341 กับ 343 คู่กันบ้าง"
- "พ.ร.บ.คอมพิวเตอร์ มาตราไหนใช้กับเคสนี้"

ถ้าอยากรันเอง (Windows เปลี่ยน `python3` เป็น `python`):

```bash
cd ~/.claude/skills/ocs-law-lookup      # Windows: cd $env:USERPROFILE\.claude\skills\ocs-law-lookup
python3 scripts/law_grep.py --list                 # ตัวบทที่มีในเครื่อง
python3 scripts/law_grep.py -s 341                 # ป.อ. มาตรา 341
python3 scripts/law_grep.py "ปล่อยชั่วคราว"         # ค้นคำ
python3 scripts/ocs_search.py "เครื่องสำอาง"        # ค้นกฎหมายฉบับอื่น (ออนไลน์)
python3 scripts/deka_cite.py 341 --with 343           # เลขฎีกาที่อ้างมาตรา (ในเครื่อง)
python3 scripts/deka_search.py "ฉ้อโกงประชาชน"      # ค้นฎีกา (ออนไลน์)
```

## มีอะไรมาให้บ้าง

```
SKILL.md              คำสั่งที่ Claude อ่าน
scripts/
  law_grep.py         ค้นตัวบทในเครื่อง (ไม่ต้องต่อเน็ต)
  ocs_search.py       ค้นกฎหมายจาก ocs.go.th
  ocs_getdoc.py       ดึงตัวบทรายมาตราเต็มฉบับ → เพิ่มเข้า corpus เองได้
  deka_search.py      ค้นคำพิพากษาฎีกา
  deka_cite.py        ฎีกาที่อ้างมาตรานี้ (ดัชนีในเครื่อง ไม่ต้องต่อเน็ต)
  _http.py            ตัวจัดการ HTTP (แก้ปัญหา cert ของเว็บราชการ)
corpus/               ตัวบทออฟไลน์
  penal_code.md              ประมวลกฎหมายอาญา (490 มาตรา)
  crim_proc_code.md          ประมวลกฎหมายวิธีพิจารณาความอาญา (396 มาตรา)
  police_act_2565.md         พ.ร.บ.ตำรวจแห่งชาติ พ.ศ. 2565 (181 มาตรา)
  deka_cite_index.json.gz    ดัชนีเลขฎีกา → มาตราที่อ้าง (ใช้กับ deka_cite.py)
references/           runbook API + กับดักที่เจอจริง + รหัสกฎหมาย
```

## ข้อจำกัด (อ่านก่อนใช้กับงานจริง)

- **ตัวบทใน `corpus/` คือภาพ ณ วันที่ดึง (21 ก.ค. 2569)** ไม่อัปเดตเอง
  กฎหมายที่แก้บ่อยให้ดึงใหม่: `python3 scripts/ocs_getdoc.py --name penal -o corpus/penal_code.md`
- ฎีกาตัวเต็มต้องต่อเน็ต และช้าได้ถึง ~2 นาทีต่อคำค้น
- `deka_cite.py` ใช้ดัชนีข้อมูลเปิด [phoneee/thai-legal-corpus](https://huggingface.co/datasets/phoneee/thai-legal-corpus) (CC-BY 4.0)
  มี 70,387 เลขฎีกาถึงปี 2568 แต่**ไม่ครบทุกเรื่อง** และมีแค่เลขฎีกา + มาตราที่อ้าง ไม่มีคำวินิจฉัย
- **สกิลไม่ได้ตัดสินคดีให้** — มันดึงของจริงมาให้อ่าน การปรับบทยังเป็นงานของคนใช้

## ไฟล์ในชุดนี้

| ไฟล์ | คืออะไร |
|---|---|
| [SKILL.md](SKILL.md) | ตัวสกิล — วางลง `.claude/skills/ocs-law-lookup/` แล้วใช้ได้เลย |
| [corpus/penal_code.md](corpus/penal_code.md) | ประมวลกฎหมายอาญา (ตัวบทเต็ม) |
| [corpus/crim_proc_code.md](corpus/crim_proc_code.md) | ประมวลกฎหมายวิธีพิจารณาความอาญา (ตัวบทเต็ม) |
| [corpus/police_act_2565.md](corpus/police_act_2565.md) | พ.ร.บ.ตำรวจแห่งชาติ 2565 (ตัวบทเต็ม) |
| [references/ocs_api.md](references/ocs_api.md) | payload/endpoint ของ ocs.go.th |
| [references/deka_api.md](references/deka_api.md) | payload/endpoint ของ deka.supremecourt.or.th |
| [references/law_ids.md](references/law_ids.md) | ตารางรหัสกฎหมาย (lawId) ที่ใช้บ่อย |
| `scripts/` | `ocs_search.py` · `ocs_getdoc.py` · `deka_search.py` · `deka_cite.py` · `law_grep.py` |

## สิทธิ์การใช้

- โค้ดในชุดนี้: MIT
- ตัวบทใน `corpus/` ดึงจาก ocs.go.th: กฎหมายไม่มีลิขสิทธิ์ตาม พ.ร.บ.ลิขสิทธิ์ พ.ศ. 2537 มาตรา 7
- `corpus/deka_cite_index.json.gz` ทำจาก [phoneee/thai-legal-corpus](https://huggingface.co/datasets/phoneee/thai-legal-corpus) (CC-BY 4.0) เก็บแค่เลขฎีกาและมาตราที่อ้าง
- คำพิพากษาฎีกาเป็นลิขสิทธิ์ศาลฎีกา สคริปต์ดึงทีละเรื่องเท่าที่ใช้ ห้ามดึงทีละมากๆ
