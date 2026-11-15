# P._.A Dorm Auto Login

สคริปต์ Python ที่ล็อกอินอินเทอร์เน็ตหอพักให้เองโดยไม่ต้องเปิดเบราว์เซอร์ และล็อกอินใหม่อัตโนมัติเมื่อเน็ตหลุด
สำหรับ captive portal แบบ **MikroTik Hotspot (CHAP login)**

> Auto-login script for MikroTik Hotspot captive portals. Pure standard library, no dependencies. [English README](README.en.md)

```
██████╗                █████╗
██╔══██╗              ██╔══██╗
██████╔╝              ███████║
██╔═══╝               ██╔══██║
██║     ██╗███████╗██╗██║  ██║
╚═╝     ╚═╝╚══════╝╚═╝╚═╝  ╚═╝
```

## Features

- ล็อกอินเองด้วย HTTP request (ไม่ต้องใช้ Chrome / Selenium)
- ตรวจว่าเน็ตหลุดทุก 10 วินาที แล้ว re-login อัตโนมัติ
- อ่านผลจาก portal แยกกรณี: รหัสผ่านผิด, เครื่องล็อกอินเต็ม, ต่อ portal ไม่ได้
- หยุดพักเมื่อรหัสผ่านถูกปฏิเสธติดกัน ป้องกันบัญชีโดนล็อก
- รอแบบ exponential backoff เมื่อล็อกอินไม่ผ่าน
- ป้องกันเปิดซ้อนสองตัว, log หมุนไฟล์อัตโนมัติ
- หน้าจอสถานะสด + แบนเนอร์ ASCII

## Requirements

- Python 3.9 ขึ้นไป (ทดสอบใน CI ด้วย 3.9, 3.11, 3.13)
- ไม่ต้องติดตั้งไลบรารีเพิ่ม (ใช้เฉพาะ standard library)

## Quick start

```bash
git clone https://github.com/<your-name>/pa-dorm-autologin.git
cd pa-dorm-autologin
python autologin.py
```

รันครั้งแรกจะถาม username / password แล้วบันทึกลง `autologin.json`
(พิมพ์รหัสผ่านแล้วไม่ขึ้นจอ) หรือคัดลอก `autologin.example.json` เป็น `autologin.json` แล้วแก้เองก็ได้

ถ้าอยากกรอกใหม่ ลบ `autologin.json` แล้วรันอีกครั้ง

> `autologin.json` เก็บเป็นข้อความธรรมดา และถูกใส่ใน `.gitignore` แล้ว **ห้าม commit ไฟล์นี้**

## ปรับให้ตรงกับ portal ของคุณ

แก้ค่าด้านบนของ `autologin.py`:

| ตัวแปร | ความหมาย |
|---|---|
| `BASE` | ที่อยู่ portal เช่น `http://10.0.6.1` |
| `INTERVAL` | เช็กเน็ตทุกกี่วินาที (ไม่แนะนำต่ำกว่า 10) |
| `BAD_PASS_LIMIT` / `BAD_PASS_PAUSE` | รหัสผ่านผิดติดกันกี่ครั้งแล้วหยุดพัก / พักกี่วินาที |
| `CHECKS` | URL ที่ใช้ตรวจว่าออนไลน์จริง |

## How it works

หน้า login ของ MikroTik hash รหัสผ่านฝั่งเบราว์เซอร์ก่อนส่ง:

```
password = MD5( chap-id + รหัสผ่าน + chap-challenge )
```

`chap-id` กับ `chap-challenge` ฝังอยู่ใน JavaScript ของหน้า login และเปลี่ยนทุกครั้งที่โหลดหน้า สคริปต์จึงทำตามนี้ทุกรอบ:

1. `GET /login` แล้วดึง chap-id / challenge ด้วย regex จาก `hexMD5('...' + ... + '...')`
2. คำนวณ MD5 ให้ตรงกับที่เบราว์เซอร์ทำ
3. `POST /login` ด้วย `username`, `password` (ค่า hash), `dst`, `popup`
4. ยืนยันผลด้วยการเช็กอินเทอร์เน็ตจริง (`generate_204`) ไม่เชื่อแค่ HTTP 200

ถ้า portal ของคุณไม่ใช่ MikroTik หรือแก้หน้า login ไว้ ให้ดู request ใน DevTools (Network → POST `login`) แล้วปรับ `make_hash()` / `login()` / `classify()`

## รันเองตอนเปิดเครื่อง (Windows)

1. รันใน terminal หนึ่งครั้งให้ `autologin.json` ถูกสร้างก่อน
2. เปิด **Task Scheduler** → **Create Task...**
3. **Triggers**: At log on
4. **Actions**: Start a program
   - Program: path ของ `pythonw.exe` (ไม่เปิดหน้าต่างดำ)
   - Arguments: path เต็มของ `autologin.py`
   - Start in: โฟลเดอร์ที่เก็บสคริปต์
5. **Settings**: เอาติ๊ก "Stop the task if it runs longer than" ออก

ดู log ได้ที่ `autologin.log` ข้างสคริปต์

## Troubleshooting

| อาการ | สาเหตุที่น่าจะเป็น |
|---|---|
| `portal ปฏิเสธรหัสผ่าน` | username/password ใน `autologin.json` ผิด |
| `ต่อ portal ไม่ได้` | ไม่ได้อยู่ในเครือข่ายหอ หรือ `BASE` ผิด |
| `หา hexMD5 ... ไม่เจอ` | portal เปลี่ยนหน้า login ต้องปรับ regex |
| `P._.A รันอยู่แล้ว` | มีอีกตัวรันอยู่ ปิดตัวเก่าก่อน |

## Disclaimer

ใช้กับบัญชีของตัวเองเท่านั้น และตรวจสอบกฎเครือข่ายของหอพัก/สถาบันก่อนใช้งาน ผู้เขียนไม่รับผิดชอบต่อการใช้งานที่ผิดกฎ

## Credits

สไตล์แบนเนอร์ ASCII (`CONNECTED` / `LOST`) ได้แรงบันดาลใจจาก `authen.py` ของ CE-HOUSE

## License

MIT - ดูไฟล์ [LICENSE](LICENSE)

## Development

```bash
python -m unittest discover -s tests -v
```

เทสต์ทั้งหมดทำงานออฟไลน์ (สูตร hash, การอ่านผลจาก portal, backoff, โลโก้) และ GitHub Actions รันให้อัตโนมัติทุกครั้งที่ push
