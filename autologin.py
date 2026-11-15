#  P._.A  -  Dorm Auto Login v2  (MikroTik Hotspot / CHAP)
#  ไม่ใช้ import ตรง ๆ ใช้ __import__ แทน
#
#  รันครั้งแรกในเทอร์มินัล: จะถามรหัสผู้ใช้/รหัสผ่านแล้วเก็บใน autologin.json
#  (ลบไฟล์นั้นถ้าอยากกรอกใหม่)

request = __import__("urllib.request", fromlist=["x"])
parse = __import__("urllib.parse", fromlist=["x"])
hashlib = __import__("hashlib")
getpass = __import__("getpass")
random = __import__("random")
shutil = __import__("shutil")
signal = __import__("signal")
socket = __import__("socket")
json = __import__("json")
re = __import__("re")
time = __import__("time")
os = __import__("os")
sys = __import__("sys")

# ================= ตั้งค่า =================
BASE = "http://10.0.6.1"
INTERVAL = 10                 # เช็กเน็ตทุกกี่วินาที
MAX_BACKOFF = 300             # ล็อกอินไม่ผ่านติดกัน จะรอนานขึ้นแต่ไม่เกินนี้ (วินาที)
BAD_PASS_LIMIT = 3            # รหัสผ่านถูกปฏิเสธติดกันกี่ครั้งแล้วหยุดพัก
BAD_PASS_PAUSE = 600          # หยุดพักกี่วินาที (กันบัญชีโดนล็อก)
LOG_MAX_BYTES = 1_000_000     # log เกินนี้จะหมุนไฟล์
LOCK_PORT = 47653             # กันเปิดซ้อนสองตัว
CHECKS = [                    # (url, status ที่ต้องได้, ข้อความที่ต้องมี)  ผ่านอันไหนก็ถือว่าออนไลน์
    ("http://connectivitycheck.gstatic.com/generate_204", 204, None),
    ("http://detectportal.firefox.com/success.txt", 200, "success"),
]
# ==========================================

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(HERE, "autologin.log")
CONFIG_FILE = os.path.join(HERE, "autologin.json")
UA = {"User-Agent": "Mozilla/5.0"}
LOCK = None
os.system("")  # เปิดสี ANSI บน Windows

C = {"r": "\033[91m", "g": "\033[92m", "y": "\033[93m", "b": "\033[94m",
     "m": "\033[95m", "c": "\033[96m", "w": "\033[97m", "d": "\033[90m",
     "0": "\033[0m"}

# ---------- ASCII art ----------
GLYPH = {
    "P": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔═══╝ ", "██║     ", "╚═╝     "],
    ".": ["   ", "   ", "   ", "   ", "██╗", "╚═╝"],
    "_": ["        ", "        ", "        ", "        ", "███████╗", "╚══════╝"],
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
}
LOGO = ["".join(GLYPH[ch][i] for ch in "P._.A") for i in range(6)]
CONNECTED = [
    " ██████╗ ██████╗ ███╗   ██╗███╗   ██╗███████╗ ██████╗████████╗███████╗██████╗ ",
    "██╔════╝██╔═══██╗████╗  ██║████╗  ██║██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗",
    "██║     ██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██║        ██║   █████╗  ██║  ██║",
    "██║     ██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██║        ██║   ██╔══╝  ██║  ██║",
    "╚██████╗╚██████╔╝██║ ╚████║██║ ╚████║███████╗╚██████╗   ██║   ███████╗██████╔╝",
    " ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═╝   ╚══════╝╚═════╝ ",
]
LOST = [
    "██╗      ██████╗ ███████╗████████╗",
    "██║     ██╔═══██╗██╔════╝╚══██╔══╝",
    "██║     ██║   ██║███████╗   ██║   ",
    "██║     ██║   ██║╚════██║   ██║   ",
    "███████╗╚██████╔╝███████║   ██║   ",
    "╚══════╝ ╚═════╝ ╚══════╝   ╚═╝   ",
]
RAINBOW = ["r", "y", "g", "c", "b", "m"]


# ---------- แสดงผล / log ----------
def term_width():
    return shutil.get_terminal_size((100, 20)).columns - 1


def status(text, color="w"):
    """บรรทัดสถานะที่อัปเดตทับที่เดิม"""
    print("\r" + C[color] + text[:term_width()].ljust(term_width()) + C["0"], end="", flush=True)


def rotate_log():
    try:
        if os.path.getsize(LOG_FILE) > LOG_MAX_BYTES:
            os.replace(LOG_FILE, LOG_FILE + ".old")
    except OSError:
        pass


def log(msg, color="w", tag="x"):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print("\r" + " " * term_width() + "\r", end="")
    print(f"    {C['d']}{stamp}{C['0']} {C['c']}[{tag}]{C['0']} {C[color]}{msg}{C['0']}")
    rotate_log()
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{stamp} [{tag}] {msg}\n")
    except OSError:
        pass


def banner(rows, colors):
    print("\r" + " " * term_width())
    for i, row in enumerate(rows):
        print("    " + C[colors[i % len(colors)]] + row + C["0"])
    print()


def fmt(sec):
    sec = int(sec)
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


# ---------- ตั้งค่า / ป้องกันเปิดซ้อน ----------
def single_instance():
    global LOCK
    LOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        LOCK.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        print("P._.A รันอยู่แล้ว (ปิดตัวเก่าก่อนถึงจะรันใหม่ได้)")
        sys.exit(0)


def load_config():
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg["username"], cfg["password"].encode()
    if not (sys.stdin and sys.stdin.isatty()):
        log("ไม่พบ autologin.json - รันครั้งแรกในเทอร์มินัลเพื่อกรอกรหัสก่อน", "r", "!")
        sys.exit(1)
    user = input("Username: ").strip()
    pw = getpass.getpass("Password (พิมพ์แล้วไม่ขึ้นจอ): ")
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"username": user, "password": pw}, f, ensure_ascii=False, indent=2)
    print("บันทึกใน autologin.json แล้ว")
    return user, pw.encode()


# ---------- เช็กเน็ต ----------
class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


check_opener = request.build_opener(NoRedirect)


def probe(url, code, text):
    try:
        r = check_opener.open(request.Request(url, headers=UA), timeout=5)
        if r.status != code:
            return False
        return text is None or text in r.read(64).decode("ascii", "ignore")
    except Exception:
        return False   # โดน redirect, timeout, ต่อไม่ได้ = ไม่ออนไลน์


def is_online():
    return any(probe(*c) for c in CHECKS)


# ---------- ล็อกอิน (CHAP) ----------
def unescape(s):
    s = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), s)
    s = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), s)
    return s.encode("latin-1")


def make_hash(html, password):
    m = re.search(r"hexMD5\(\s*'([^']*)'\s*\+\s*[^+]+?\+\s*'([^']*)'\s*\)", html)
    if not m:
        return None
    return hashlib.md5(unescape(m.group(1)) + password + unescape(m.group(2))).hexdigest()


def classify(body):
    """อ่านผลจากหน้าที่ portal ตอบกลับ (ข้อความเป็นค่าเริ่มต้นของ MikroTik)"""
    low = body.lower()
    if "invalid username or password" in low or "invalid password" in low:
        return "bad_password"
    if "no more sessions" in low:
        return "limit"
    if "already logged in" in low:
        return "already"
    return "sent"


def login(user, password):
    """คืน (ผล, รายละเอียด): sent / already / bad_password / limit / no_hash / portal_down"""
    try:
        with request.urlopen(request.Request(BASE + "/login", headers=UA), timeout=8) as r:
            html = r.read().decode("utf-8", "ignore")
    except Exception as e:
        return "portal_down", str(e)

    h = make_hash(html, password)
    if h is None:
        if "logout" in html.lower():
            return "already", ""
        return "no_hash", ""

    data = parse.urlencode({"username": user, "password": h,
                            "dst": "http://google.com", "popup": "true"}).encode()
    req = request.Request(BASE + "/login", data=data, headers={
        **UA, "Content-Type": "application/x-www-form-urlencoded",
        "Referer": BASE + "/login?", "Origin": BASE})
    try:
        with request.urlopen(req, timeout=10) as r:
            return classify(r.read().decode("utf-8", "ignore")), ""
    except Exception as e:
        return "portal_down", str(e)


def backoff(fails):
    return min(INTERVAL * 2 ** min(fails, 10), MAX_BACKOFF) + random.uniform(0, 3)


# ---------- ลูปหลัก ----------
class Stats:
    def __init__(self):
        self.state = None        # None / "on" / "off"
        self.lost_at = 0
        self.online_since = 0
        self.started = time.time()
        self.relogins = 0
        self.down_total = 0
        self.checks = 0
        self.fails = 0
        self.bad = 0


def on_online(st):
    if st.state == "on":
        return
    down = time.time() - st.lost_at if st.state == "off" else 0
    banner(CONNECTED, ["g", "g", "c", "c", "b", "b"])
    if st.state == "off":
        st.relogins += 1
        st.down_total += down
        log(f"กลับมาออนไลน์ (หลุดไป {fmt(down)})", "g", "+")
        log(f"re-login {st.relogins} ครั้ง | รวมหลุด {fmt(st.down_total)} | "
            f"รันมา {fmt(time.time() - st.started)}", "d", "x")
    else:
        log("ออนไลน์อยู่แล้ว", "g", "+")
    st.state, st.online_since, st.fails, st.bad = "on", time.time(), 0, 0


def on_offline(st, user, password):
    """จัดการตอนออฟไลน์ 1 รอบ แล้วคืนจำนวนวินาทีที่ต้องรอก่อนเช็กครั้งถัดไป"""
    if st.state != "off":
        st.state, st.lost_at = "off", time.time()
        banner(LOST, ["r", "r", "y", "y", "r", "r"])
        log("เน็ตหลุด -> เริ่มล็อกอินใหม่", "r", "!")

    result, info = login(user, password)

    if result in ("sent", "already"):
        time.sleep(2)
        if is_online():
            on_online(st)
            return INTERVAL
        st.fails += 1
        log(f"ส่งล็อกอินแล้วแต่ยังออฟไลน์ (ครั้งที่ {st.fails})", "y", "!")
        return backoff(st.fails)

    if result == "portal_down":
        log(f"ต่อ portal ไม่ได้ - อยู่ในเครือข่ายหอหรือเปล่า? ({info[:60]})", "y", "!")
        return 15   # ไม่นับเป็นล็อกอินล้มเหลว เพราะยังไปไม่ถึงหน้า login

    if result == "bad_password":
        st.bad += 1
        log(f"portal ปฏิเสธรหัสผ่าน ({st.bad}/{BAD_PASS_LIMIT})", "r", "!")
        if st.bad >= BAD_PASS_LIMIT:
            log(f"หยุดพัก {BAD_PASS_PAUSE // 60} นาที กันบัญชีโดนล็อก - เช็ก autologin.json", "r", "!")
            st.bad = 0
            return BAD_PASS_PAUSE
        return backoff(st.bad)

    if result == "limit":
        log("จำนวนเครื่องที่ล็อกอินพร้อมกันเต็ม - logout เครื่องอื่นก่อน", "r", "!")
        return 60

    st.fails += 1
    log("หา hexMD5 ในหน้า login ไม่เจอ (portal เปลี่ยนหน้า?)", "r", "!")
    return backoff(st.fails)


def show_status(st, next_check):
    wait = max(0, int(next_check - time.time()))
    if st.state == "on":
        status(f"● ONLINE  up {fmt(time.time() - st.online_since)} | "
               f"checks {st.checks} | re-logins {st.relogins} | next {wait}s", "g")
    else:
        status(f"○ OFFLINE  down {fmt(time.time() - st.lost_at)} | retry in {wait}s", "r")


def bye(*_):
    print()
    log("Good bye! P._.A", "m", "x")
    sys.exit(0)


def main():
    single_instance()
    user, password = load_config()
    signal.signal(signal.SIGINT, bye)

    banner(LOGO, RAINBOW)
    log(f"User: {user} | Portal: {BASE} | Interval: {INTERVAL}s", "w", "x")
    print(f"    {C['d']}{'─' * 62}{C['0']}")

    st = Stats()
    next_check = 0
    while True:
        if time.time() >= next_check:
            st.checks += 1
            if is_online():
                on_online(st)
                next_check = time.time() + INTERVAL
            else:
                next_check = time.time() + on_offline(st, user, password)
        show_status(st, next_check)
        time.sleep(1)


if __name__ == "__main__":
    main()
