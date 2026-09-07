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
import urllib.request
import urllib.parse
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


GDRIVE_CREDS = Path("/Users/shayanisse/.config/gdrive-mcp/.gdrive-server-credentials.json")
GDRIVE_KEYS = Path("/Users/shayanisse/.config/gdrive-mcp/gcp-oauth.keys.json")


def get_gdrive_token():
    try:
        with open(GDRIVE_CREDS) as f:
            creds = json.load(f)
        with open(GDRIVE_KEYS) as f:
            keys = json.load(f).get("installed", {})
        params = {
            "client_id": keys["client_id"],
            "client_secret": keys["client_secret"],
            "refresh_token": creds["refresh_token"],
            "grant_type": "refresh_token",
        }
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=urllib.parse.urlencode(params).encode(),
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["access_token"]
    except Exception:
        return None


def find_stories_doc_today():
    try:
        with open(GDRIVE_CREDS) as f:
            creds = json.load(f)
        with open(GDRIVE_KEYS) as f:
            keys = json.load(f).get("installed", {})
        # Refresh token
        r = subprocess.run([
            "curl", "-s", "-X", "POST", "https://oauth2.googleapis.com/token",
            "-d", f"client_id={keys['client_id']}",
            "-d", f"client_secret={keys['client_secret']}",
            "-d", f"refresh_token={creds['refresh_token']}",
            "-d", "grant_type=refresh_token"
        ], capture_output=True, text=True, timeout=10)
        token = json.loads(r.stdout).get("access_token", "")
        if not token:
            return None
        today_iso = date.today().isoformat() + "T00:00:00Z"
        q = f"name contains 'Stories Didier' and mimeType = 'application/vnd.google-apps.document' and modifiedTime > '{today_iso}'"
        r2 = subprocess.run([
            "curl", "-s",
            f"https://www.googleapis.com/drive/v3/files?q={urllib.parse.quote(q)}&fields=files(id,name)&pageSize=5",
            "-H", f"Authorization: Bearer {token}"
        ], capture_output=True, text=True, timeout=15)
        files = json.loads(r2.stdout).get("files", [])
        if files:
            doc_id = files[0]["id"]
            return {"name": files[0].get("name", ""), "url": f"https://docs.google.com/document/d/{doc_id}/edit"}
        return None
    except Exception:
        return None


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



def hhmm(heures):
    """9.46 → '9h28'."""
    if not heures:
        return None
    h = int(heures)
    return f"{h}h{int(round((heures - h) * 60)):02d}"


def moyenne_21j(days, chemin, sauf_date):
    """Moyenne d'une métrique Whoop sur les 21 derniers jours, la nuit en cours exclue."""
    vals = []
    for d in days[-22:]:
        if d.get("date") == sauf_date:
            continue
        cur = d.get("whoop") or {}
        for k in chemin:
            cur = (cur or {}).get(k) if isinstance(cur, dict) else None
        if isinstance(cur, (int, float)) and cur:
            vals.append(cur)
    return sum(vals) / len(vals) if vals else None


def bloc_sommeil(data, today_data, today):
    """La nuit qui vient de se terminer, telle que la Whoop l'a mesurée.

    C'est le coeur du brief depuis qu'il se declenche au reveil : la nuit est
    classee sur sa date de REVEIL, donc celle qui vient de finir est celle
    d'aujourd'hui, pas celle d'hier."""
    w = (today_data or {}).get("whoop") or {}
    slp, rec = w.get("sleep") or {}, w.get("recovery") or {}
    if not slp.get("coucher"):
        return []

    out = ["😴 <b>TA NUIT</b>"]
    duree = hhmm(slp.get("heures_sommeil"))
    out.append(f"  {slp['coucher']} → {slp.get('lever', '?')}" + (f" · {duree} de sommeil" if duree else ""))

    detail = []
    if slp.get("deep_h"):
        detail.append(f"Profond {hhmm(slp['deep_h'])}")
    if slp.get("rem_h"):
        detail.append(f"REM {hhmm(slp['rem_h'])}")
    if slp.get("performance_pct"):
        detail.append(f"Besoin couvert {slp['performance_pct']:.0f}%")
    if detail:
        out.append("  " + " · ".join(detail))

    physio = []
    if rec.get("score"):
        physio.append(f"Recovery {rec['score']}%")
    if rec.get("hrv"):
        physio.append(f"HRV {rec['hrv']:.0f}")
    if rec.get("rhr"):
        physio.append(f"FC repos {rec['rhr']}")
    if physio:
        out.append("  " + " · ".join(physio))

    # Comparaisons : une valeur seule ne dit rien, c'est l'ecart qui parle.
    days = data.get("days", [])
    ecarts = []
    for libelle, chemin, valeur, sens in [
        ("Régularité", ["sleep", "consistency_pct"], slp.get("consistency_pct"), "haut"),
        ("FC repos", ["recovery", "rhr"], rec.get("rhr"), "bas"),
    ]:
        moy = moyenne_21j(days, chemin, today)
        if valeur is None or moy is None:
            continue
        delta = valeur - moy
        # Sous 1 point l'écart disparaît à l'affichage arrondi : une flèche entre
        # deux nombres identiques donne l'impression d'un bug. On n'affiche rien.
        if abs(delta) < 1:
            continue
        fleche = "↑" if delta > 0 else "↓"
        bon = (delta > 0) if sens == "haut" else (delta < 0)
        ecarts.append(f"{libelle} {valeur:.0f} {fleche} (moy 21j {moy:.0f})" + (" ✓" if bon else ""))
    for e in ecarts:
        out.append(f"  {e}")

    if slp.get("dette_h") and slp["dette_h"] >= 1:
        out.append(f"  ⚠ Dette de sommeil : {hhmm(slp['dette_h'])}")

    out.append("")
    return out


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
    lines += bloc_sommeil(data, today_data, today)

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
        ib = p.get("intrabeaute") or {}
        rates = [k for k in ("base_animale", "sans_transforme",
                             "sans_sucre_alcool_cafe", "hydratation")
                 if ib.get(k) is False]
        if rates:
            libelles = {"base_animale": "base animale", "sans_transforme": "ultra-transformé",
                        "sans_sucre_alcool_cafe": "sucre/alcool/café", "hydratation": "hydratation"}
            manques = ", ".join(libelles[k] for k in rates)
            alerts.append(f"🥩 Intrabeauté hier : {len(rates)}/4 non tenus ({manques}).")
        elif p.get("nutrition_clean") is False:
            alerts.append("🍔 Goyslop hier — discipline absolue aujourd'hui.")
        if ib.get("lumiere_matin") is False:
            alerts.append("🌅 Lumière du matin ratée hier — yeux dehors au lever, peau couverte.")

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

    # STORIES DOC (dimanche uniquement)
    if date.today().weekday() == 6:  # dimanche = 6
        stories_doc = find_stories_doc_today()
        if stories_doc:
            lines.append("")
            lines.append("📋 <b>STORIES DIDIER — COPYWRITING PRÊT</b>")
            lines.append(f"  Valide ici : {stories_doc['url']}")

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
