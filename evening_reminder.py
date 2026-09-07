#!/usr/bin/env python3
"""
JARVIS Evening Reminder — 22h daily

Le brief du matin (morning_brief.py, 8h30) est conservé et reste le porteur des
échéances de tâches, des relances CRM et du doc stories du dimanche. Seules ses
questions sur le sommeil ont été retirées : la Whoop les rend inutiles.

Ce qui n'est PLUS demandé ici, parce que la Whoop le mesure :
  - heure de coucher et de lever
  - gym et type de séance

Ce qui est demandé en plus : les 6 items du protocole intrabeauté.
Les 4 items nutrition doivent tous être répondus, sinon le pilier Physique
reste plafonné à 16 points sur 20. Voir 2 CAPS/JARVIS/PROTOCOLE INTRABEAUTE.md
"""

import subprocess

BOT_TOKEN = "8997450587:AAHjCjOVRipxIEzgFxAsqtxkCMyRtkmq35Y"
CHAT_ID = "5351269136"

def build_message():
    lines = ["⏰ <b>JARVIS CHECK-IN SOIR</b>", "",
             "Envoie-moi un vocal avec toutes ces réponses dans l'ordre :", "",
             "💼 <b>BUSINESS</b>",
             "→ Combien de DMs envoyés ?",
             "→ Calls bookés / closés ?",
             "→ Qu'est-ce que t'as fait exactement aujourd'hui ? (tout, sans filtre)",
             "",
             "🥩 <b>INTRABEAUTÉ</b> (les 4 premiers = 4 pts, tout ou rien)",
             "→ Base animale au repas principal ? (viande rouge grasse, œufs, poisson gras, foie)",
             "→ Zéro ultra-transformé et zéro huile de graine ?",
             "→ Zéro sucre ajouté, zéro alcool, zéro café ?",
             "→ Hydratation : eau minérale, zéro sel ajouté ?",
             "→ Lumière du matin dans les yeux, peau couverte ?",
             "→ Filtre chaud le soir + chambre noire et fraîche ?",
             "→ Foie et huîtres cette semaine, combien de fois ?",
             "",
             "🍽️ <b>REPAS</b>",
             "→ Ce que t'as mangé aujourd'hui",
             "",
             "🕌 <b>SPIRITUEL</b>",
             "→ Fajr ? (oui/non)",
             "→ Prières sur 5 ?",
             "→ Coran ? (oui/non)",
             "",
             "🧠 <b>COGNITIF</b>",
             "→ Heures de deep work + sur quoi ?",
             "→ Duolingo russe ? (oui/non + minutes)",
             "→ Qu'est-ce que t'as appris ou appliqué aujourd'hui ?",
             "",
             "⚡ <b>MENTAL</b>",
             "→ Énergie (1-10) ?",
             "→ Focus (1-10) ?",
             "→ No PMO ? (oui/non)",
             "→ NSDR ? (oui/non)",
             "",
             "📲 <b>SOCIAL</b>",
             "→ Interaction haute valeur ?",
             "→ Contenu posté ? (oui/non)",
             "",
             "Et envoie le screenshot Screen Time (Back Tap double).",
             "",
             "<i>Sommeil et gym ne sont plus demandés, la Whoop les lit seule.</i>"]

    lines += ["", "— JARVIS"]
    return "\n".join(lines)


def main():
    msg = build_message()
    subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        "-d", f"chat_id={CHAT_ID}",
        "-d", "parse_mode=HTML",
        "--data-urlencode", f"text={msg}",
    ], capture_output=True, text=True)
    print("Evening reminder sent.")


if __name__ == "__main__":
    main()
