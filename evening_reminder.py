#!/usr/bin/env python3
"""
JARVIS Evening Reminder — 22h daily
Reminds Shayan to send Screen Time + business check-in
"""

import subprocess

BOT_TOKEN = "8997450587:AAHjCjOVRipxIEzgFxAsqtxkCMyRtkmq35Y"
CHAT_ID = "5351269136"

msg = """⏰ <b>JARVIS CHECK-IN SOIR</b>

Envoie-moi un vocal avec toutes ces réponses dans l'ordre :

💼 <b>BUSINESS</b>
→ Combien de DMs envoyés ?
→ Calls bookés / closés ?
→ Qu'est-ce que t'as fait exactement aujourd'hui ? (tout, sans filtre)

🏋️ <b>PHYSIQUE</b>
→ Gym ? (oui/non + type de séance)
→ À quelle heure tu t'es réveillé ce matin ? (ex: "9h30")
→ No goyslop ? (oui/non + ce que t'as mangé)

🕌 <b>SPIRITUEL</b>
→ Fajr ? (oui/non)
→ Prières sur 5 ?
→ Coran ? (oui/non)

🧠 <b>COGNITIF</b>
→ Heures de deep work + sur quoi ? (ex: "3h sur stories Didier")
→ Duolingo russe ? (oui/non + combien de minutes)
→ Apprentissage notable du jour ? (optionnel)
→ Qu'est-ce que t'as appris ou appliqué aujourd'hui ?

⚡ <b>MENTAL</b>
→ Énergie de la journée (1-10) ?
→ Focus (1-10) ?
→ No PMO ? (oui/non)
→ NSDR ? (oui/non — 10min allongé audio YouTube)

📲 <b>SOCIAL</b>
→ Interaction haute valeur (réseau, mentor, partenaire) ?
→ Contenu posté ? (oui/non)

Et envoie le screenshot Screen Time (Back Tap double).

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
