#!/usr/bin/env python3
"""HTTP helper ที่ทนกับเซิร์ฟเวอร์ราชการไทย

ทำไมต้องมี: `www.ocs.go.th` ส่ง certificate chain ไม่ครบ (ขาด intermediate)
→ Python urllib ตาย `CERTIFICATE_VERIFY_FAILED` ทั้งที่เบราว์เซอร์/curl เปิดได้
(เบราว์เซอร์กับ curl ไปดึง intermediate มาเองได้ Python ไม่ทำให้)

วิธีแก้ที่ใช้: ลอง urllib ก่อน → ถ้าล้มเพราะ SSL ค่อย fallback ไป curl
(ไม่ปิด verify ทิ้ง — curl ยังตรวจ cert ตามปกติ)
"""
from __future__ import annotations

import json as _json
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request


class HttpError(RuntimeError):
    pass


def _curl_post(url: str, *, body: bytes, headers: dict, timeout: int) -> bytes:
    if not shutil.which("curl"):
        raise HttpError(
            f"เชื่อมต่อ {url} ด้วย Python ไม่ได้ (cert chain ฝั่งเซิร์ฟเวอร์ไม่ครบ) "
            "และไม่พบคำสั่ง curl ในเครื่อง — ติดตั้ง curl แล้วลองใหม่"
        )
    # -f: HTTP 4xx/5xx = error ชัดๆ แทนที่จะได้หน้า error HTML แล้วไปพังตอนอ่าน JSON
    cmd = ["curl", "-sSf", "--max-time", str(timeout), "-X", "POST", url, "--data-binary", "@-"]
    for key, value in headers.items():
        cmd += ["-H", f"{key}: {value}"]
    proc = subprocess.run(cmd, input=body, capture_output=True)
    if proc.returncode != 0:
        raise HttpError(f"curl ล้มเหลว ({proc.returncode}): {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


def post(url: str, *, form: dict | None = None, json_body: dict | None = None,
         headers: dict | None = None, timeout: int = 60) -> bytes:
    """POST แบบ form-urlencoded หรือ JSON — คืน response body ดิบ"""
    headers = dict(headers or {})
    headers.setdefault("User-Agent", "Mozilla/5.0")

    if json_body is not None:
        body = _json.dumps(json_body).encode()
        headers.setdefault("Content-Type", "application/json")
    else:
        body = urllib.parse.urlencode(form or {}).encode()
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.URLError as exc:
        if "SSL" not in str(exc.reason) and "CERTIFICATE" not in str(exc.reason).upper():
            raise HttpError(f"เรียก {url} ไม่สำเร็จ: {exc.reason}") from exc
        return _curl_post(url, body=body, headers=headers, timeout=timeout)
    except (TimeoutError, OSError) as exc:
        # หมดเวลาระหว่างอ่านคำตอบไม่ได้มาเป็น URLError (Python 3.10+) → ต้องจับแยก
        raise HttpError(f"เรียก {url} ไม่สำเร็จ (เซิร์ฟเวอร์ช้าหรือหลุด): {exc}") from exc


def post_json(url: str, **kwargs) -> dict:
    raw = post(url, **kwargs)
    try:
        return _json.loads(raw)
    except ValueError as exc:
        head = raw[:200].decode(errors="replace")
        raise HttpError(f"คำตอบจาก {url} ไม่ใช่ JSON: {head}") from exc
