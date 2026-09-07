#!/usr/bin/env python3
"""
JARVIS Evening Reminder — 22h daily

Depuis le 08/09/2026 c'est le SEUL check-in de la journée. Le brief du matin a
été coupé : la Whoop donne le sommeil et la séance sans rien demander, et le
reste du message matinal était soit statique, soit basé sur des champs que le
DAILY LOG ne remplit plus. Les deux blocs qui vivaient encore là-bas (échéances
de tâches, doc stories du dimanche) ont été rapatriés ici.

Ce qui n'est PLUS demandé, parce que la Whoop le mesure :
  - heure de coucher et de lever
  - gym et type de séance

Ce qui est demandé en plus : les 6 items du protocole intrabeauté.
Les 4 items nutrition doivent tous être répondus, sinon le pilier Physique
reste plafonné à 16 points sur 20. Voir 2 CAPS/JARVIS/PROTOCOLE INTRABEAUTE.md
"""

import json
import subprocess
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

DATA_JSON = Path("/Users/shayanisse/jarvis-dashboard/data.json")
BOT_TOKEN = "8997450587:AAHjCjOVRipxIEzgFxAsqtxkCMyRtkmq35Y"
CHAT_ID = "5351269136"

GDRIVE_CREDS = Path("/Users/shayanisse/.config/gdrive-mcp/.gdrive-server-credentials.json")
GDRIVE_KEYS = Path("/Users/shayanisse/.config/gdrive-mcp/gcp-oauth.keys.json")


def find_stories_doc_today():
    """Doc de copywriting stories Didier modifié aujourd'hui (dimanche)."""
    try:
        with open(GDRIVE_CREDS) as f:
            creds = json.load(f)
        with open(GDRIVE_KEYS) as f:
            keys = json.load(f).get("installed", {})
        r = subprocess.run([
            "curl", "-s", "-X", "POST", "https://oauth2.googleapis.com/token",
            "-d", f"client_id={keys['client_id']}",
            "-d", f"client_secret={keys['client_secret']}",
            "-d", f"refresh_token={creds['refresh_token']}",
            "-d", "grant_type=refresh_token",
        ], capture_output=True, text=True, timeout=10)
        token = json.loads(r.stdout).get("access_token", "")
        if not token:
            return None
        today_iso = date.today().isoformat() + "T00:00:00Z"
        q = ("name contains 'Stories Didier' and "
             "mimeType = 'application/vnd.google-apps.document' and "
             f"modifiedTime > '{today_iso}'")
        r2 = subprocess.run([
            "curl", "-s",
            "https://www.googleapis.com/drive/v3/files"
            f"?q={urllib.parse.quote(q)}&fields=files(id,name)&pageSize=5",
            "-H", f"Authorization: Bearer {token}",
        ], capture_output=True, text=True, timeout=15)
        files = json.loads(r2.stdout).get("files", [])
        if files:
            return f"https://docs.google.com/document/d/{files[0]['id']}/edit"
        return None
    except Exception:
        return None


def taches_echeances():
    """Tâches dont l'échéance tombe dans les 3 jours ou est dépassée."""
    try:
        with open(DATA_JSON) as f:
            data = json.load(f)
    except Exception:
        return []
    out = []
    for t in data.get("tasks", []):
        if t.get("statut") == "done" or not t.get("echeance"):
            continue
        try:
            delta = (date.fromisoformat(t["echeance"]) - date.today()).days
        except Exception:
            continue
        if delta > 3:
            continue
        if delta < 0:
            timing = f"en retard de {abs(delta)} jour(s)"
        elif delta == 0:
            timing = "AUJOURD'HUI"
        elif delta == 1:
            timing = "demain"
        else:
            timing = f"dans {delta} jours"
        out.append((delta, f"  → {t.get('titre', '?')} — {timing}"))
    return [line for _, line in sorted(out)]


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

    taches = taches_echeances()
    if taches:
        lines += ["", "📋 <b>ÉCHÉANCES PROCHES</b>"] + taches

    if date.today().weekday() == 6:
        doc = find_stories_doc_today()
        if doc:
            lines += ["", "📋 <b>STORIES DIDIER — COPYWRITING PRÊT</b>",
                      f"  Valide ici : {doc}"]

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
