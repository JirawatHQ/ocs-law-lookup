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

อัปเดตรุ่นใหม่:
- macOS / Linux: `git -C ~/.claude/skills/ocs-law-lookup pull`
- Windows: `git -C "$env:USERPROFILE\.claude\skills\ocs-law-lookup" pull`

ถ้า pull ไม่ผ่านเพราะเคยแก้ไฟล์ในโฟลเดอร์เอง ให้ย้ายไฟล์ที่แก้ไปเก็บก่อน แล้วสั่ง
`git -C <โฟลเดอร์> reset --hard origin/main` ตามด้วย pull ใหม่ (ไฟล์ใน `corpus/local/` ไม่โดนลบ เพราะ git ไม่ได้ติดตาม)

### เคยติดตั้งแบบ zip / มีโฟลเดอร์ `ocs-law-lookup` อยู่แล้วแต่ไม่ได้มาจาก git clone

`git pull` ใช้ไม่ได้กับโฟลเดอร์แบบนี้ ให้ทำ 4 ขั้น:
1. **ย้าย**โฟลเดอร์เดิมไปไว้นอก `skills` (เช่น `~/.claude/skills-backup/ocs-law-lookup-old`) อย่าลบ
   และอย่าวางสำรองไว้ใน `skills` ไม่งั้น Claude เห็นสกิลชื่อซ้ำสองตัว
2. clone ใหม่ตามคำสั่งด้านบน
3. ตัวบทที่เคยเพิ่มเอง ก๊อปไปไว้ที่ `corpus/local/` ของรุ่นใหม่ (ฉบับที่รุ่นใหม่มีแล้วไม่ต้องก๊อป)
4. รัน `python3 scripts/law_grep.py --list` ต้องเห็นไฟล์ใน `corpus/local` ด้วย และ `git status` ต้องไม่มีไฟล์ค้าง

### ห้ามแก้ไฟล์ในโฟลเดอร์สกิล

แก้ SKILL.md หรือไฟล์อื่นที่มากับสกิลแล้ว `git pull` รอบหน้าจะไม่ยอมอัปเดต
- ตัวบทที่อยากเพิ่ม → `corpus/local/` (git ไม่ติดตาม)
- อยากให้ Claude รู้จักกฎหมาย/วิธีทำงานเพิ่ม → เขียนใน `CLAUDE.md` ของตัวเอง ไม่ใช่ SKILL.md

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
  selfcheck.py        ตรวจว่าสกิลพร้อมใช้ (ส่งผลให้คนดูแลเวลาใช้ไม่ได้)
  _http.py            ตัวจัดการ HTTP (แก้ปัญหา cert ของเว็บราชการ)
corpus/               ตัวบทออฟไลน์
  penal_code.md              ประมวลกฎหมายอาญา
  crim_proc_code.md          ประมวลกฎหมายวิธีพิจารณาความอาญา
  civil_code.md              ประมวลกฎหมายแพ่งและพาณิชย์
  police_act_2565.md         พ.ร.บ.ตำรวจแห่งชาติ พ.ศ. 2565
  aml_act_2542.md            พ.ร.บ.ป้องกันและปราบปรามการฟอกเงิน พ.ศ. 2542
  nacc_act_2561.md           พ.ร.บ.ประกอบรัฐธรรมนูญว่าด้วยการป้องกันและปราบปรามการทุจริต พ.ศ. 2561
  admin_procedure_2539.md    พ.ร.บ.วิธีปฏิบัติราชการทางปกครอง พ.ศ. 2539
  deka_cite_index.json.gz    ดัชนีเลขฎีกา → มาตราที่อ้าง (ใช้กับ deka_cite.py)
references/           runbook API + กับดักที่เจอจริง + รหัสกฎหมาย
```

## ใช้ไม่ได้ / ผลแปลก

รัน `python3 scripts/selfcheck.py` แล้วส่งผลทั้งหมดให้คนดูแล (บอกเวอร์ชัน, ไฟล์ที่ถูกแก้, ตัวบทซ้ำ, ต่อเว็บได้ไหม)
ดูว่ามีอะไรเปลี่ยนในแต่ละรุ่น: [CHANGELOG.md](CHANGELOG.md)

## ข้อจำกัด (อ่านก่อนใช้กับงานจริง)

- **ตัวบทใน `corpus/` คือภาพ ณ วันที่ดึง (21 ต.ค. 2569)** ไม่อัปเดตเอง ทุกผลค้นบอกวันที่นี้กำกับ
  ดึงฉบับล่าสุดเก็บในเครื่อง: `python3 scripts/ocs_getdoc.py --name penal -o corpus/local/penal_code.md`
  (`--name` รับ penal / crimproc / civil / police / aml / nacc / admin) ไฟล์ใน `corpus/local/` ใช้แทนของเดิมอัตโนมัติ
  **อย่าเขียนทับไฟล์ใน `corpus/` ตรงๆ** ไม่งั้น git pull รอบหน้าจะไม่ยอมอัปเดต
- ฎีกาตัวเต็มต้องต่อเน็ต และช้าได้ถึง ~2 นาทีต่อคำค้น ถ้าเว็บศาลล่มหรือเปลี่ยนหน้าตา สคริปต์จะบอกตรงๆ
  ว่าติดต่อไม่ได้/อ่านไม่ออก (ไม่ตอบว่า "ไม่พบ")
- `deka_cite.py` ใช้ดัชนีข้อมูลเปิด [phoneee/thai-legal-corpus](https://huggingface.co/datasets/phoneee/thai-legal-corpus) (CC-BY 4.0)
  มี 70,384 เลขฎีกาถึงปี 2568 แต่**ไม่ครบทุกเรื่อง** และมีแค่เลขฎีกา + มาตราที่อ้าง ไม่มีคำวินิจฉัย
- **สกิลไม่ได้ตัดสินคดีให้** — มันดึงของจริงมาให้อ่าน การปรับบทยังเป็นงานของคนใช้

## ไฟล์ในชุดนี้

| ไฟล์ | คืออะไร |
|---|---|
| [SKILL.md](SKILL.md) | ตัวสกิล — วางลง `.claude/skills/ocs-law-lookup/` แล้วใช้ได้เลย |
| [corpus/penal_code.md](corpus/penal_code.md) | ประมวลกฎหมายอาญา (ตัวบทเต็ม) |
| [corpus/crim_proc_code.md](corpus/crim_proc_code.md) | ประมวลกฎหมายวิธีพิจารณาความอาญา (ตัวบทเต็ม) |
| [corpus/police_act_2565.md](corpus/police_act_2565.md) | พ.ร.บ.ตำรวจแห่งชาติ 2565 (ตัวบทเต็ม) |
| [corpus/civil_code.md](corpus/civil_code.md) | ประมวลกฎหมายแพ่งและพาณิชย์ (ตัวบทเต็ม) |
| [corpus/aml_act_2542.md](corpus/aml_act_2542.md) | พ.ร.บ.ป้องกันและปราบปรามการฟอกเงิน 2542 (ตัวบทเต็ม) |
| [corpus/nacc_act_2561.md](corpus/nacc_act_2561.md) | พ.ร.บ.ป.ป.ช. 2561 (ตัวบทเต็ม) |
| [corpus/admin_procedure_2539.md](corpus/admin_procedure_2539.md) | พ.ร.บ.วิธีปฏิบัติราชการทางปกครอง 2539 (ตัวบทเต็ม) |
| [references/ocs_api.md](references/ocs_api.md) | payload/endpoint ของ ocs.go.th |
| [references/deka_api.md](references/deka_api.md) | payload/endpoint ของ deka.supremecourt.or.th |
| [references/law_ids.md](references/law_ids.md) | ตารางรหัสกฎหมาย (lawId) ที่ใช้บ่อย |
| `scripts/` | `ocs_search.py` · `ocs_getdoc.py` · `deka_search.py` · `deka_cite.py` · `law_grep.py` |

## สิทธิ์การใช้

- โค้ดในชุดนี้: MIT
- ตัวบทใน `corpus/` ดึงจาก ocs.go.th: กฎหมายไม่มีลิขสิทธิ์ตาม พ.ร.บ.ลิขสิทธิ์ พ.ศ. 2537 มาตรา 7
- `corpus/deka_cite_index.json.gz` ดัดแปลงจาก [phoneee/thai-legal-corpus](https://huggingface.co/datasets/phoneee/thai-legal-corpus)
  โดย phoneee (CC-BY 4.0) ส่วนที่ดัดแปลง: เก็บแค่เลขฎีกาและมาตราที่อ้าง, จัดรูปเลขมาตรา, ตัดแถวที่ไม่มีเลขฎีกา
- คำพิพากษาฎีกาเป็นลิขสิทธิ์ศาลฎีกา สคริปต์ดึงทีละเรื่องเท่าที่ใช้ ห้ามดึงทีละมากๆ
