# encTimelineID ที่ยืนยันแล้ว + วิธีหาของฉบับอื่น

`encTimelineID` คือรหัสที่ใช้กับ `ocs_getdoc.py` เพื่อดึงตัวบทรายมาตรา

## ยืนยันแล้ว (ดึงได้จริง)

| กฎหมาย | encTimelineID | ย่อ |
|---|---|---|
| ประมวลกฎหมายอาญา | `K2dTMURyaDllOXJVWVZqZGJLK09pdz09` | `--name penal` |
| ประมวลกฎหมายวิธีพิจารณาความอาญา | `UVdzUTNzUFZlT3VBOEw2allVWTZxZz09` | `--name crimproc` |
| พระราชบัญญัติตำรวจแห่งชาติ พ.ศ. 2565 | `UEY5OTdqYWRyZE9IM1NqTE5ZLzk4dz09` | `--name police` |

> `--name` ค้นชื่อเต็มใน ocs เพื่อเอา id ล่าสุดทุกครั้ง ตารางนี้เป็นทางสำรองเมื่อค้นไม่เจอ
> (ตรวจ 2026-10-21: id ทั้ง 3 ฉบับยังตรงกับที่ ocs ใช้อยู่)
> (ดึงครั้งล่าสุด: ป.อาญา แก้ไขถึงฉบับที่ 30/2568 · พ.ร.บ.ตำรวจ 2565 ใช้บังคับ 2022-10-17)

## หา id ของกฎหมายฉบับอื่น

```bash
python3 scripts/ocs_search.py "ชื่อกฎหมาย" --title-only
# ผลค้นจะพิมพ์บรรทัด "ตัวบทรายมาตรา: python3 ocs_getdoc.py <id> -o out.md" ให้เลย
python3 scripts/ocs_getdoc.py <id> -o corpus/local/ชื่อไฟล์.md
```

ไฟล์ที่ได้จะเข้าระบบ `law_grep.py` อัตโนมัติ (สแกน `corpus/` และ `corpus/local/`)

## หมวดที่ใช้บ่อย (`--category`)

`1D` = ประมวลกฎหมาย — ใช้กรองเวลาหาตัวประมวล เช่น
```bash
python3 scripts/ocs_search.py "" --category 1D -n 50
```

## กฎหมายที่ ocs ไม่มี

- **คำพิพากษาฎีกา** → `deka_search.py` (คนละแหล่ง)
- **ประมวลระเบียบการตำรวจ / คำสั่ง ตร.** → ไม่ได้เผยแพร่ผ่าน ocs
  ต้นฉบับ PDF สแกน: เผยแพร่โดยกองกฎหมาย สกบ. ผ่าน policeworker.one
- **กฎ ก.ตร. รายฉบับ** → มีบางส่วนใน ocs ค้นด้วยชื่อเต็ม เช่น "กฎ ก.ตร. ว่าด้วย..."
