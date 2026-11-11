# =====================================================================
# keygen.py - KAVIN V6 Premium Keygen (Hourly & Daily Support)
# =====================================================================

import os
import random
import string
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.prompt import Prompt
from rich.box import ROUNDED, DOUBLE, HEAVY

SECRET_KEY = b"KavinV6SecretKey2024!@#$%^&*()" 
console = Console()

def clear_screen():
    try: os.system('cls' if os.name == 'nt' else 'clear')
    except Exception: pass

def show_banner():
    clear_screen()
    console.print()
    title = Text("⚡ KAVIN V6 - KEYGEN ⚡", style="bold bright_magenta", justify="center")
    sub = Text("Premium License Generator (Hourly & Daily)", style="italic bright_black", justify="center")
    console.print(Panel(Align.center(Text.assemble(title, "\n", sub)), border_style="cyan", box=DOUBLE, padding=(1, 2)))
    console.print()

def generate_key(days_float: float = 365.0) -> str:
    try:
        int_days = int(days_float) if days_float >= 1 else 1
        rand_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        payload = f"V6-KAVIN-{int_days}-{rand_part}"
        sig = hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()[:4].upper()
        
        # Key အသစ်ပုံစံ - V6-KAVIN-365-XXXXXXXX-YYYY
        key = f"V6-KAVIN-{int_days}-{rand_part}-{sig}"
        return key
    except Exception:
        return ""

def ask_duration():
    """သက်တမ်းကို နာရီ (သို့) ရက်နဲ့ မေးမယ့် Function"""
    console.print("\n[bold cyan]သက်တမ်းကို ဘယ်လို ထုတ်မလဲ?[/]")
    console.print("  [bold bright_green]1.[/] ⏱ နာရီ (Hours) နဲ့ ထုတ်မယ်")
    console.print("  [bold bright_green]2.[/] 📅 ရက် (Days) နဲ့ ထုတ်မယ်")
    
    choice = Prompt.ask("  [bright_cyan]➜ Select[/]").strip()
    
    if choice == "1":
        try:
            hours_str = Prompt.ask("[bold cyan]➜ Enter Hours (e.g. 1, 12, 24)[/]").strip()
            hours = float(hours_str) if hours_str else 24.0
            days_float = hours / 24.0 # နာရီကို ရက်အဖြစ် ပြောင်းမယ်
            return days_float, f"{hours} Hours"
        except ValueError:
            return 1.0, "1 Day"
    else:
        try:
            days_str = Prompt.ask("[bold cyan]➜ Enter Days (e.g. 1, 7, 365)[/]").strip()
            days = float(days_str) if days_str else 365.0
            return days, f"{days} Days"
        except ValueError:
            return 365.0, "365 Days"

def show_menu():
    show_banner()
    menu = Table.grid(padding=(0, 2), expand=True)
    menu.add_column(justify="center")
    menu.add_column(justify="left")
    
    menu.add_row("[bold bright_green]1.[/]", "🔑 Generate single key")
    menu.add_row("[bold bright_green]2.[/]", "📦 Generate multiple keys")
    menu.add_row("[bold bright_red]0.[/]", "🚪 Exit")
    
    console.print(Panel(menu, title="[bold yellow]MAIN MENU[/]", border_style="cyan", box=ROUNDED, padding=(1, 2)))

def main():
    while True:
        show_menu()
        choice = Prompt.ask("[bold bright_cyan]➜ Select Option[/]").strip()

        if choice == "0":
            console.print("\n[bold yellow]✨ Goodbye! ✨[/]\n")
            break

        elif choice == "1":
            show_banner()
            days, duration_text = ask_duration()
            
            key = generate_key(days) 
            expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M')

            res_table = Table(show_header=False, box=ROUNDED, border_style="green", expand=True)
            res_table.add_column("Info", style="bold cyan")
            res_table.add_column("Value", style="bold white")
            res_table.add_row("🔑 Key", f"[bold bright_green]{key}[/]")
            res_table.add_row("⏱ Duration", duration_text)
            res_table.add_row("⏳ Expiry", expiry)

            console.print("\n")
            console.print(Panel(res_table, title="[bold bright_green]✓ V6 KEY GENERATED[/]", border_style="green", box=HEAVY))
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]", default="")

        elif choice == "2":
            show_banner()
            try:
                count_str = Prompt.ask("[bold cyan]➜ How many keys?[/]").strip()
                count = int(count_str)
            except ValueError:
                console.print("[bold red]❌ Invalid input[/bold red]")
                time.sleep(1.5)
                continue

            days, duration_text = ask_duration()

            keys = [generate_key(days) for _ in range(count)]
            
            console.print("\n")
            k_table = Table(show_header=True, header_style="bold magenta", box=ROUNDED, border_style="cyan")
            k_table.add_column("No.", justify="center")
            k_table.add_column("License Key", style="bold green")
            for i, k in enumerate(keys, 1):
                k_table.add_row(str(i), k)
                
            console.print(Panel(k_table, title=f"[bold cyan]📦 {count} KEYS GENERATED ({duration_text})[/]", border_style="cyan", box=HEAVY))
            
            save = Prompt.ask("\n[bold yellow]➜ Save to keys.txt? (y/n)[/]").strip().lower()
            if save == "y":
                with open("keys.txt", "w") as f:
                    for k in keys: f.write(k + "\n")
                console.print("[bold green]✓ Saved to keys.txt[/bold green]")
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]", default="")

        else:
            console.print("[bold red]❌ Invalid choice![/bold red]")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]Exiting...[/bold red]\n")
