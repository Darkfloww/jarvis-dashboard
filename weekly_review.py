#!/usr/bin/env python3
"""
JARVIS Weekly Review — runs every Sunday
Analyzes 7-day trends and sends a full review to Telegram
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
    subprocess.run(cmd, capture_output=True, text=True)


def load_data():
    with open(DATA_JSON) as f:
        return json.load(f)


def avg(vals):
    v = [x for x in vals if x]
    return round(sum(v) / len(v), 1) if v else 0


def build_weekly_review(data):
    today = date.today()
    last_7 = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    days_map = {d["date"]: d for d in data.get("days", [])}
    week_days = [days_map[d] for d in last_7 if d in days_map]

    if not week_days:
        return None

    lines = []
    lines.append(f"📊 <b>JARVIS WEEKLY REVIEW — Semaine du {last_7[0]} au {last_7[-1]}</b>")
    lines.append("")

    # SCORES
    scores = [d.get("score", 0) for d in week_days]
    avg_score = avg(scores)
    best_score = max(scores) if scores else 0
    days_above_80 = sum(1 for s in scores if s >= 80)
    lines.append(f"<b>Score moyen : {avg_score}/100</b> | Meilleur : {best_score} | Jours solides (80+) : {days_above_80}/7")
    lines.append("")

    # PAR PILLIER
    lines.append("<b>Scores moyens par pillier :</b>")
    pilliers = [
        ("Business", "business", 30),
        ("Physique", "physique", 20),
        ("Spirituel", "spirituel", 20),
        ("Cognitif", "cognitif", 15),
        ("Mental", "mental", 10),
        ("Social", "social", 5),
    ]
    for name, key, max_pts in pilliers:
        vals = [d.get(key, {}).get("score", 0) for d in week_days]
        a = avg(vals)
        pct = round(a / max_pts * 100)
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        lines.append(f"  {name:10} {bar} {a}/{max_pts}")
    lines.append("")

    # BUSINESS METRICS
    total_dms = sum(d.get("business", {}).get("dms", 0) or 0 for d in week_days)
    total_calls_b = sum(d.get("business", {}).get("calls_bookes", 0) or 0 for d in week_days)
    total_calls_c = sum(d.get("business", {}).get("calls_closes", 0) or 0 for d in week_days)
    lines.append("<b>Business semaine :</b>")
    lines.append(f"  DMs total : {total_dms}/14 (objectif 7×2)")
    lines.append(f"  Calls bookés : {total_calls_b} | Calls closés : {total_calls_c}")
    lines.append("")

    # FAJR
    fajr_days = sum(1 for d in week_days if d.get("spirituel", {}).get("fajr") is True)
    prieres_avg = avg([d.get("spirituel", {}).get("prieres", 0) for d in week_days])
    lines.append("<b>Spirituel :</b>")
    lines.append(f"  Fajr : {fajr_days}/7 jours | Prières moyenne : {prieres_avg}/5")
    lines.append("")

    # SLEEP
    sleep_avg = avg([d.get("physique", {}).get("heures_sommeil", 0) for d in week_days])
    gym_days = sum(1 for d in week_days if d.get("physique", {}).get("gym") is True)
    goyslop_days = sum(1 for d in week_days if d.get("physique", {}).get("nutrition_clean") is False)
    lines.append("<b>Physique :</b>")
    lines.append(f"  Gym : {gym_days}/7 | Sommeil moyen : {sleep_avg}h | Goyslop : {goyslop_days}j")
    lines.append("")

    # PMO STREAK
    streak = 0
    for d in reversed(data.get("days", [])):
        if d.get("mental", {}).get("no_pmo") is True:
            streak += 1
        elif d.get("mental", {}).get("no_pmo") is False:
            break
    lines.append(f"🔥 <b>Streak No PMO actuel : {streak} jours</b>")
    lines.append("")

    # VERDICT
    lines.append("<b>Verdict semaine :</b>")
    issues = []
    if avg_score < 60: issues.append("Score global faible — exécution à revoir")
    if total_dms < 100: issues.append(f"Outreach insuffisant ({total_dms}/140 DMs)")
    if fajr_days < 5: issues.append(f"Fajr : {fajr_days}/7 — pas acceptable")
    if goyslop_days > 0: issues.append(f"Goyslop {goyslop_days} jour(s) — discipline alimentaire")
    if gym_days < 4: issues.append(f"Gym seulement {gym_days}/7 — augmente la fréquence")

    if not issues:
        lines.append("  Semaine solide. Maintiens la cadence et scale.")
    else:
        for i in issues:
            lines.append(f"  ⚠ {i}")

    lines.append("")
    lines.append("<b>Focus semaine prochaine :</b>")

    # Top priority for next week
    min_pillar = min(pilliers, key=lambda x: avg([d.get(x[1], {}).get("score", 0) or 0 for d in week_days]) / x[2])
    lines.append(f"  Pillier le plus faible : {min_pillar[0]} — priorité #1")
    lines.append("  Continue l'outreach daily sans exception")
    lines.append("")
    lines.append("— JARVIS")

    return "\n".join(lines)


def main():
    data = load_data()
    review = build_weekly_review(data)
    if not review:
        print("Pas assez de données pour la review")
        return
    print(review)
    send_telegram(review)
    print("Weekly review sent.")


if __name__ == "__main__":
    main()
