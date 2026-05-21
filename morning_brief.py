#!/usr/bin/env python3
"""
JARVIS Morning Brief
Sends a proactive Telegram message each morning with:
- Yesterday's performance summary
- Today's priorities (based on gaps)
- Alerts for critical issues
- CRM follow-ups due
"""

import json
import subprocess
from datetime import date, timedelta
from pathlib import Path

DATA_JSON = Path("/Users/shayanisse/jarvis-dashboard/data.json")
BOT_TOKEN = "8997450587:AAHjCjOVRipxIEzgFxAsqtxkCMyRtkmq35Y"
CHAT_ID = "5351269136"


def send_telegram(text):
    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        "-d", f"chat_id={CHAT_ID}",
        "-d", "parse_mode=HTML",
        "--data-urlencode", f"text={text}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def load_data():
    if not DATA_JSON.exists():
        return None
    with open(DATA_JSON) as f:
        return json.load(f)


def get_day(data, date_str):
    return next((d for d in data.get("days", []) if d["date"] == date_str), None)


def calc_streak(days):
    s = 0
    for d in reversed(days):
        if d.get("mental", {}).get("no_pmo") is True:
            s += 1
        elif d.get("mental", {}).get("no_pmo") is False:
            break
    return s


def score_label(score):
    if score >= 80: return "SOLIDE"
    if score >= 60: return "CORRECT"
    if score > 0:   return "FAIBLE"
    return "NON RENSEIGNÉ"


def score_emoji(score):
    if score >= 80: return "🟣"
    if score >= 60: return "🟡"
    if score > 0:   return "🔴"
    return "⚪"


def build_brief(data):
    today = str(date.today())
    yesterday = str(date.today() - timedelta(days=1))

    days = data.get("days", [])
    yesterday_data = get_day(data, yesterday)
    today_data = get_day(data, today)
    streak = calc_streak(days)

    lines = []

    # HEADER
    import locale
    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
    except Exception:
        pass
    from datetime import datetime
    today_fr = datetime.now().strftime("%A %d %B").capitalize()
    lines.append(f"⚡ <b>JARVIS MORNING BRIEF — {today_fr}</b>")
    lines.append("")

    # YESTERDAY PERFORMANCE
    if yesterday_data:
        score = yesterday_data.get("score", 0)
        emoji = score_emoji(score)
        label = score_label(score)
        lines.append(f"{emoji} <b>Hier : {score}/100 — {label}</b>")

        b = yesterday_data.get("business", {})
        p = yesterday_data.get("physique", {})
        sp = yesterday_data.get("spirituel", {})
        c = yesterday_data.get("cognitif", {})
        m = yesterday_data.get("mental", {})

        # Quick recap
        dms = b.get("dms", 0) or 0
        gym = "✓" if p.get("gym") else "✗"
        fajr = "✓" if sp.get("fajr") else "✗"
        dw = c.get("deep_work_heures", 0) or 0
        pmo = "✓" if m.get("no_pmo") else "✗" if m.get("no_pmo") is False else "?"

        lines.append(f"  DMs {dms}/2 | Gym {gym} | Fajr {fajr} | Deep work {dw}h | No PMO {pmo}")
        lines.append("")
    else:
        lines.append("⚪ Pas de données pour hier.")
        lines.append("")

    # CRITICAL ALERTS
    alerts = []
    if yesterday_data:
        sp = yesterday_data.get("spirituel", {})
        p = yesterday_data.get("physique", {})
        m = yesterday_data.get("mental", {})
        b = yesterday_data.get("business", {})

        if sp.get("fajr") is False:
            alerts.append("☾ Fajr raté hier — c'est la base. Couche-toi avant 23h ce soir.")
        if (b.get("dms") or 0) < 1:
            alerts.append("💬 0 DMs hier — l'outreach n'a pas été fait. C'est la priorité #1 ce matin.")
        if (m.get("screen_time_reseaux_min") or 0) > 120:
            from math import floor
            mins = m.get("screen_time_reseaux_min", 0)
            h, mi = floor(mins/60), mins%60
            alerts.append(f"📱 {h}h{str(mi).zfill(2)} de réseaux hier — laisse ton téléphone jusqu'à 18h.")
        if p.get("nutrition_clean") is False:
            alerts.append("🍔 Goyslop hier — discipline absolue aujourd'hui.")

    if alerts:
        lines.append("🚨 <b>POINTS CRITIQUES</b>")
        for a in alerts:
            lines.append(f"  {a}")
        lines.append("")

    # TODAY'S PRIORITIES (TOP 3)
    lines.append("🎯 <b>PRIORITÉS AUJOURD'HUI</b>")

    priorities = []

    # Always: outreach if yesterday was low
    if yesterday_data:
        dms_y = (yesterday_data.get("business", {}).get("dms") or 0)
        if dms_y < 2:
            priorities.append("1. 2 DMs outreach de qualité — ciblés, personnalisés, à fort levier.")
        else:
            priorities.append("1. 2 DMs outreach de qualité — maintenir la cadence.")
    else:
        priorities.append("1. 2 DMs outreach de qualité — commence maintenant.")

    # Deep work block
    priorities.append("2. Bloc deep work 3h minimum — ferme les notifs, pas de réseaux avant 18h.")

    # Delivery Didier
    priorities.append("3. Delivery Didier — avance sur la vidéo pre-call ou les stories cette semaine.")

    for p in priorities:
        lines.append(f"  {p}")
    lines.append("")

    # CRM FOLLOW-UPS
    crm = data.get("crm", {}).get("prospects", [])
    followups = [p for p in crm if p.get("status") in ("responded", "call_scheduled") or
                 (p.get("next_action_date") and p.get("next_action_date") <= today)]
    if followups:
        lines.append("📞 <b>RELANCES AUJOURD'HUI</b>")
        for f in followups[:5]:
            lines.append(f"  → {f.get('name', '?')} ({f.get('status', '?')}) — {f.get('next_action', '')}")
        lines.append("")

    # STREAK
    if streak > 0:
        lines.append(f"🔥 <b>Streak No PMO : {streak} jour{'s' if streak > 1 else ''}</b> — protège-le.")
    else:
        lines.append("⚡ Streak No PMO : 0 — aujourd'hui ça recommence.")
    lines.append("")

    # TASK REMINDERS
    tasks = data.get("tasks", [])
    due_soon = []
    for t in tasks:
        if t.get("statut") == "done":
            continue
        echeance = t.get("echeance", "")
        if not echeance:
            continue
        try:
            from datetime import datetime
            due = date.fromisoformat(echeance)
            delta = (due - date.today()).days
            if delta <= 3:
                due_soon.append((t, delta))
        except Exception:
            pass

    if due_soon:
        lines.append("📋 <b>TÂCHES — ÉCHÉANCES PROCHES</b>")
        for t, delta in due_soon:
            if delta < 0:
                timing = f"⚠ En retard de {abs(delta)} jour(s) !"
            elif delta == 0:
                timing = "⚠ À faire AUJOURD'HUI"
            elif delta == 1:
                timing = "Demain"
            else:
                timing = f"Dans {delta} jours ({t['echeance']})"
            lines.append(f"  → {t['titre']} — {timing}")
        lines.append("")

    # SLEEP QUESTION
    lines.append("")
    lines.append("😴 <b>Question sommeil :</b> À quelle heure t'es couché hier soir ?")
    lines.append("(Réponds directement ici, ex: \"2h30\")")

    # CLOSER
    lines.append("")
    lines.append("— JARVIS")

    return "\n".join(lines)


def main():
    data = load_data()
    if not data:
        print("data.json introuvable")
        return

    brief = build_brief(data)
    print(brief)
    print("\n--- Sending to Telegram ---")
    result = send_telegram(brief)
    print(result)


if __name__ == "__main__":
    main()
