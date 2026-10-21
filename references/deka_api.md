# deka.supremecourt.or.th — ค้นคำพิพากษาศาลฎีกา

ระบบสืบค้นฎีกาของศาลฎีกา ค้นฟรี ไม่ต้อง login (login ใช้แค่ bookmark)
**ลิขสิทธิ์ศาลฎีกา — ค้นเฉพาะเรื่องที่ใช้จริงในคดี ห้าม bulk-scrape**

## วิธีค้น

```
GET  https://deka.supremecourt.or.th/          ← เอา session cookie ก่อน
POST https://deka.supremecourt.or.th/search    ← คืน HTML (ไม่ใช่ JSON)
```

ไม่มี CAPTCHA บนฟอร์มค้น (CAPTCHA อยู่แค่ login/สมัคร)

### ฟิลด์พื้นฐาน
`search_word` (คำค้น หลายคำ = AND ของ token) · `search_doctype=1` (คำพิพากษาศาลฎีกา) ·
`search_type` (`1`=ฉบับย่อ, `2`=ฉบับเต็ม) · `search_deka_start_year` / `search_deka_end_year` (พ.ศ.) ·
`start=true` · `search_form_type=basic`

### ฟิลด์ขั้นสูง (ตรงงานสอบสวน)
`adv_search_law_section` (มาตรา) · `adv_search_law_name` (ชื่อกฎหมาย) · `adv_search_deka_no` (เลขฎีกา) ·
`adv_search_judge` · `adv_search_litigant` (คู่ความ) · `adv_search_black_no_of_scourt` (เลขคดีดำ)

## อ่านผลลัพธ์

ผลค้นฝัง**ทั้งย่อและตัวเต็ม**มาในหน้าเดียว ไม่ต้องยิง detail แยก:

| element | คือ |
|---|---|
| `<li id="short_text_docid_<id>">` | ฎีกาย่อ |
| `<li id="long_text_docid_<id>">` | คำวินิจฉัยตัวเต็ม |
| `<input id="text_bookmark_name_<id>" value="คำพิพากษาศาลฎีกาที่ X/YYYY">` | เลขฎีกาของ docid นั้น |

⚠ **บล็อกเนื้อหาเป็น `<li>` ไม่ใช่ `<div>`** — regex ที่ปิดด้วย `</div>` จะกินเนื้อรายการถัดไปมาปน
⚠ **อย่าจับคู่เลขฎีกากับเนื้อหาตามลำดับที่เจอ** — เลขปรากฏซ้ำหลายที่ต่อรายการ (รายการ + บล็อกสำหรับพิมพ์)
ให้ผูกผ่าน `text_bookmark_name_<docid>` เท่านั้น
- เลขฎีกาเดียวกันโผล่หลาย docid ได้ตามปกติ = คำพิพากษาฉบับเดียวถูกแยก entry ตามประเด็นข้อกฎหมาย

## กับดักที่เจอจริง

1. **ไม่ส่ง User-Agent = เซิร์ฟเวอร์ไม่ตอบเลย** (connection reset / timeout 60s+)
   ไม่ใช่เน็ตเสีย — ใส่ UA ของเบราว์เซอร์แล้วผ่านทันที
2. **urllib โดน reset ที่ TLS handshake** → ใช้ curl (`-c`/`-b` cookie jar)
3. **session-replay:** ถ้าส่ง params ผิด/ไม่ครบ เซิร์ฟเวอร์ **ไม่ error แต่คืนผลค้นเดิมที่ค้างใน session**
   → คนละคำค้นได้ผลชุดเดียวกันเป๊ะ เสี่ยงหลงคิดว่าเจอ
   **กันด้วย:** ยิง control query ที่ไม่เกี่ยวกัน (เช่น "ลิขสิทธิ์") เทียบ docid ถ้าชุดเดียวกัน = ผลไม่จริง
   (`deka_search.py` ทำให้อัตโนมัติแล้ว)
4. `start` ค่าที่ถูกคือ `true` ไม่ใช่ offset ตัวเลข
5. บาง query ช้า >110 วินาที → ตั้ง timeout ยาว (สคริปต์ใช้ 280s) และ retry เมื่อได้คำตอบว่าง

## แหล่งสำรอง

- `decision.coj.go.th` (สนง.ศาลยุติธรรม, คำพิพากษาเต็ม PDF) — บล็อก IP นอกไทย
- `deka.in.th` (เนติบัณฑิตยสภา) — 403 / อาจต้อง subscription
