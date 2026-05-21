#!/usr/bin/env python3
"""
JARVIS Evening Reminder — 22h daily
Reminds Shayan to send Screen Time + business check-in
"""

import subprocess

BOT_TOKEN = "8997450587:AAHjCjOVRipxIEzgFxAsqtxkCMyRtkmq35Y"
CHAT_ID = "5351269136"

msg = """⏰ <b>JARVIS — Rappel soir</b>

Avant de dormir, envoie-moi :

1. 📱 <b>Screen Time</b> — Back Tap double sur l'iPhone
2. 💼 <b>Check-in business</b> — vocal ou texte, tout ce que t'as fait aujourd'hui
3. ✅ <b>Métriques</b> (facultatif si tu veux que je les rentre) :
   Gym, prières, deep work, no goyslop, no PMO

— JARVIS"""

cmd = [
    "curl", "-s", "-X", "POST",
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    "-d", f"chat_id={CHAT_ID}",
    "-d", "parse_mode=HTML",
    "--data-urlencode", f"text={msg}"
]
subprocess.run(cmd, capture_output=True, text=True)
print("Evening reminder sent.")
