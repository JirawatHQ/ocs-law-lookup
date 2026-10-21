# ocs.go.th API — สำนักงานคณะกรรมการกฤษฎีกา

ฐานกฎหมาย**ทางการ**ของไทย ใช้ฟรี ไม่ต้อง login ไม่มี CAPTCHA
(ตัวบทกฎหมายไม่มีลิขสิทธิ์ แต่ยังควร rate-limit + cache — เป็นเซิร์ฟเวอร์ราชการ)

## 1. ค้นรายชื่อกฎหมาย — `list_table_search`

```
POST https://www.ocs.go.th/searchlaw/indexs/list_table_search
Content-Type: application/x-www-form-urlencoded
X-Requested-With: XMLHttpRequest
Referer: https://www.ocs.go.th/searchlaw
```

| พารามิเตอร์ | ค่า |
|---|---|
| `query[q]` | คำค้น (เว้นว่าง = ทั้งหมด) |
| `query[tab_type]` | `law` = ตัวบท · `comment` = ความเห็นกฤษฎีกา |
| `query[content]` | `1` = ค้นทั้งเนื้อหา · `0` = ค้นเฉพาะชื่อ |
| `query[lawCategoryName]` | รหัสหมวด — `1D` = ประมวลกฎหมาย |
| `query[stateName]` | `01,02` = ใช้บังคับ / รอใช้บังคับ |
| `query[sort]` | `date-desc` |
| `pagination[page]`, `pagination[perpage]` | แบ่งหน้า |

**Response JSON:** `meta.total` / `meta.pages` · `data[]` แต่ละฉบับมี
`lawNameTh` (ชื่อ — มี `<mark>` ครอบคำที่ match ต้องถอดออก) · `contentlaw` (สรุปย่อ) ·
`year` · `publishDate` · `fileUUID` (**ลิงก์ PDF ตัวบทเต็ม** — บางฉบับเป็น URL เต็มมาแล้ว
บางฉบับเป็น token ต้องเติม `https://www.ocs.go.th/downloadfile/`) ·
`encTimelineID` (ใช้กับ getLawDoc) · `childrens[]` (กฎลูก) · `finishNo` (ความเห็นที่เกี่ยว)

## 2. ตัวบทรายมาตรา — `getLawDoc`

**ประมวลกฎหมายไม่มี PDF** ต้องดึงทางนี้ (พ.ร.บ. ก็ดึงได้ ได้ structured ดีกว่า PDF)

```
POST https://searchlaw.ocs.go.th/ocs-api/public/doc/getLawDoc
Content-Type: application/json
```
```json
{"reqHeader": {"reqId": "1", "reqChannel": "WEB", "reqDtm": "2026-01-01 00:00:00.000",
               "reqBy": "unknow", "serviceName": "getPublicLawDoc", "uuid": "x", "sessionId": "x"},
 "reqBody": {"isTransEng": false, "timelineId": "<encTimelineID>"}}
```

`reqHeader` ใส่ค่า dummy ได้ แต่ **ต้องมีครบทุก key** ไม่งั้น validate ตก

**Response:** `respBody.lawSections[]` · `footnoteList[]` (ที่มาการแก้ไขรายมาตรา) ·
`timelines[]` (ประวัติแก้ไขทุกฉบับ) · `lawInfo` (ชื่อ/lawCode/วันบังคับใช้)

### sectionTypeId — อ่านให้ถูก ไม่งั้นแปลงผิด
| type | คือ |
|---|---|
| `4` | **มาตรา** (มี `sectionNo`) |
| `6` / `7` / `8` / `9` | ภาค / ลักษณะ / หมวด / ส่วน — **มี `sectionNo` ของตัวเองด้วย** |
| `1` | ชื่อกฎหมาย — โผล่ซ้ำทุกครั้งที่ขึ้นเอกสารใหม่ในไฟล์เดียวกัน |
| `15` / `16` / `3` / `14` | หมายเหตุ / สารบาญ / คำปรารภ / ผู้รับสนองฯ |

⚠ **กับดักที่เจอจริง:**
1. อย่าสร้าง "มาตรา X" จาก `sectionNo` เพียงอย่างเดียว — หมวด 3 จะกลายเป็นมาตรา 3
2. ไฟล์เดียวมีหลายเอกสาร: พ.ร.บ.ให้ใช้ประมวลฯ → ตัวประมวล → พ.ร.บ.แก้ไขเพิ่มเติมท้ายเล่ม 30+ ฉบับ
   แต่ละฉบับมีมาตรา 1, 2, 3 ของตัวเอง → ต้องกำกับว่ามาตราไหนของฉบับไหน
3. **ป.วิ.อาญาไม่มี section ชื่อกฎหมายของตัวประมวลเอง** (ต่างจาก ป.อาญา) — ถ้าใช้ชื่อเอกสาร
   ตัดสินอย่างเดียว ทั้งฉบับจะโดนติดป้ายเป็น "พ.ร.บ.ให้ใช้ฯ" → ให้ถือว่าเจอ ภาค/ลักษณะ = เข้าตัวประมวลแล้ว

## กับดักการเชื่อมต่อ

- **`www.ocs.go.th` ส่ง certificate chain ไม่ครบ** (ขาด intermediate) → Python urllib ตาย
  `CERTIFICATE_VERIFY_FAILED` ทั้งที่เบราว์เซอร์เปิดได้ → fallback ไป curl (ดู `scripts/_http.py`)
  `searchlaw.ocs.go.th` (getLawDoc) ไม่มีปัญหานี้
- **`PDL_CIPHER_EXCEPTION`** จาก getLawDoc = transient เมื่อยิงติดกันเร็ว ๆ → เว้นจังหวะแล้วลองใหม่ ผ่าน
