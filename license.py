# =====================================================================
# license.py - KAVIN FAST SPEED V4 License Manager
# =====================================================================

import os
import json

LICENSE_FILE = "kavin_license.json"

def check_approval():
    """
    လိုင်စင် အတည်ပြုချက် ရှိမရှိ စစ်ဆေးခြင်း။
    Returns: (is_valid: bool, expiry_msg: str)
    """
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("active", False):
                    key_type = data.get("type", "VIP Lifetime")
                    return True, f"Active ({key_type})"
        except Exception:
            pass
    return False, "Not Activated"

def activate(key):
    """
    Key ထည့်သွင်း အတည်ပြုခြင်း။
    Returns: (success: bool, message: str)
    """
    key = key.strip()
    if not key:
        return False, "Please enter a valid key!"
    
    # 💡 ဤနေရာတွင် သင်ကြိုက်နှစ်သက်ရာ Key စည်းမျဉ်းများ (သို့မဟုတ်) Admin Key များကို စစ်ဆေးနိုင်ပါသည်။
    # ဥပမာ - 'KAVIN-' ဖြင့် စသော Key များ (သို့မဟုတ်) အက္ခရာ ၆ လုံးအထက် ရှိသော Key များကို လက်ခံရန်:
    if len(key) >= 6:
        try:
            data = {
                "active": True,
                "key": key,
                "type": "VIP Access"
            }
            with open(LICENSE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True, "License Activated Successfully! 🎉"
        except Exception as e:
            return False, f"Activation Error: {e}"
    
    return False, "Invalid License Key! Contact @kavin799"
