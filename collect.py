#!/usr/bin/env python3
"""
JARVIS Data Collector
Reads: ActivityWatch API, iCloud Screen Time PNG, JARVIS DAILY LOG (Obsidian)
Outputs: data.json for the dashboard
"""

import json
import os
import re
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, date
from pathlib import Path

VAULT = Path("/Users/shayanisse/Documents/Obsidian Vault")
DAILY_LOG = VAULT / "2 CAPS/JARVIS/DAILY LOG.md"
SCREEN_TIME_PNG = Path("/Users/shayanisse/Library/Mobile Documents/com~apple~CloudDocs/Jarvis/screen_time.png")
DATA_JSON = Path("/Users/shayanisse/jarvis-dashboard/data.json")
AW_API = "http://localhost:5600/api/0/"


def load_existing_data():
    if DATA_JSON.exists():
        with open(DATA_JSON) as f:
            return json.load(f)
    return {
        "lastUpdated": str(date.today()),
        "profile": {
            "name": "Shayan",
            "goal": "Top 0.00000001%",
            "location": "Sanya, Chine",
            "patrimoine": 6000,
            "client": "Didier (~1500-1750€/mois)"
        },
        "days": []
    }


def aw_get(path):
    """Query ActivityWatch via curl with redirect following."""
    url = AW_API + path.lstrip("/")
    result = subprocess.run(
        ["curl", "-s", "-L", "--max-time", "5", url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise Exception(f"curl failed: {result.stderr}")
    return json.loads(result.stdout)


def get_aw_activity():
    """Query ActivityWatch for today's productive app usage."""
    try:
        today = str(date.today())
        buckets = aw_get("/buckets")

        # Find window watcher bucket
        window_bucket = next((b for b in buckets if 'window' in b.lower()), None)
        if not window_bucket:
            return {"status": "no_bucket", "total_min": 0, "apps": {}}

        # Get events for today — URL-encode + as %2B (AW server issue)
        start = f"{today}T00%3A00%3A00%2B00%3A00"
        end = f"{today}T23%3A59%3A59%2B00%3A00"
        events_url = f"buckets/{window_bucket}/events?start={start}&end={end}&limit=2000"
        events = aw_get(events_url)
        if isinstance(events, dict):
            raise Exception(f"AW events error: {events}")

        apps = {}
        for ev in events:
            app = ev.get("data", {}).get("app", "unknown")
            dur = ev.get("duration", 0)
            apps[app] = apps.get(app, 0) + dur

        total_sec = sum(apps.values())
        top_apps = sorted(apps.items(), key=lambda x: -x[1])[:10]

        return {
            "status": "ok",
            "total_min": round(total_sec / 60),
            "apps": {k: round(v / 60) for k, v in top_apps}
        }
    except Exception as e:
        return {"status": f"error: {e}", "total_min": 0, "apps": {}}


def parse_daily_log_entry(date_str):
    """Parse today's entry from the JARVIS DAILY LOG."""
    if not DAILY_LOG.exists():
        return {}

    content = DAILY_LOG.read_text(encoding="utf-8")

    # Strip HTML comments (<!-- ... -->) to avoid parsing the template
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

    # Find the section for today
    pattern = rf"## {re.escape(date_str)}.*?(?=## 20|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}

    section = match.group(0)
    result = {}

    def extract(label, default=None):
        m = re.search(rf"{re.escape(label)}\s*:?\s*(.+)", section, re.IGNORECASE)
        return m.group(1).strip() if m else default

    def extract_int(label, default=0):
        m = re.search(rf"{re.escape(label)}\s*:?\s*(\d+)", section, re.IGNORECASE)
        return int(m.group(1)) if m else default

    def extract_bool(label):
        m = re.search(rf"{re.escape(label)}\s*:?\s*(oui|non|yes|no|true|false)", section, re.IGNORECASE)
        if m:
            return m.group(1).lower() in ('oui', 'yes', 'true')
        return None

    def extract_float(label, default=0.0):
        m = re.search(rf"{re.escape(label)}\s*:?\s*([\d.,]+)", section, re.IGNORECASE)
        return float(m.group(1).replace(',', '.')) if m else default

    # Business
    result["business"] = {
        "dms": extract_int("DMs envoyés", extract_int("DMs outreach")),
        "calls_bookes": extract_int("Calls bookés"),
        "calls_closes": extract_int("Calls closés"),
        "commission_estimee": extract_int("Commission estimée"),
        "delivery_done": extract_bool("Delivery Didier"),
        "score": extract_int("score_business", 0)
    }

    # Physique
    gym_raw = extract("Gym")
    gym_done = None
    gym_type = ""
    if gym_raw:
        gym_done = gym_raw.lower().startswith("oui") or gym_raw.lower().startswith("yes")
        if "(" in gym_raw:
            gym_type = gym_raw[gym_raw.find("(")+1:gym_raw.find(")")]

    nutrition_clean = extract_bool("Nutrition clean") or extract_bool("no goyslop")
    repas_raw = extract("Repas")

    result["physique"] = {
        "gym": gym_done,
        "gym_type": gym_type,
        "coucher": extract("couché") or extract("Couché"),
        "lever": extract("levé") or extract("Levé"),
        "heures_sommeil": extract_float("heures") or extract_float("sommeil h"),
        "nutrition_clean": nutrition_clean,
        "repas": repas_raw or "",
        "eau_litres": extract_float("Eau"),
        "score": extract_int("score_physique", 0)
    }

    # Spirituel
    result["spirituel"] = {
        "fajr": extract_bool("Fajr"),
        "prieres": extract_int("Prières") or extract_int("prieres"),
        "coran": extract_bool("Coran"),
        "score": extract_int("score_spirituel", 0)
    }

    # Cognitif
    result["cognitif"] = {
        "deep_work_heures": extract_float("Deep work"),
        "duolingo_russe": extract_bool("Duolingo russe"),
        "duolingo_minutes": extract_int("Duolingo russe"),
        "apprentissage": extract("Apprentissage"),
        "score": extract_int("score_cognitif", 0)
    }

    # Mental
    result["mental"] = {
        "energie": extract_int("Énergie") or extract_int("Energie"),
        "focus": extract_int("Focus"),
        "screen_time_reseaux_min": extract_int("Screen time"),
        "no_pmo": extract_bool("No PMO"),
        "score": extract_int("score_mental", 0)
    }

    # Social
    result["social"] = {
        "interaction_hv": extract("Interaction HV") or extract("Interaction haute valeur"),
        "contenu_poste": extract_bool("Contenu posté"),
        "score": extract_int("score_social", 0)
    }

    # Global
    jarvis_score_match = re.search(r"SCORE JARVIS\s*:\s*(\d+)", section, re.IGNORECASE)
    result["score"] = int(jarvis_score_match.group(1)) if jarvis_score_match else 0

    feedback_match = re.search(r"FEEDBACK\s*:\s*(.+?)(?=\n##|\Z)", section, re.IGNORECASE | re.DOTALL)
    result["feedback"] = feedback_match.group(1).strip()[:300] if feedback_match else ""

    result["note"] = extract("Statut") or ""

    return result


def update_data():
    today = str(date.today())
    data = load_existing_data()

    # Check if today already has an entry
    existing_idx = next((i for i, d in enumerate(data["days"]) if d["date"] == today), None)

    # Build today's entry
    print(f"[JARVIS Collect] {today}")

    # Parse DAILY LOG
    parsed = parse_daily_log_entry(today)
    print(f"  Daily log parsed: score={parsed.get('score', 0)}")

    # Get ActivityWatch data
    aw = get_aw_activity()
    print(f"  ActivityWatch: {aw['status']} — {aw['total_min']}min")

    # Check Screen Time PNG
    screen_time_updated = False
    if SCREEN_TIME_PNG.exists():
        mtime = datetime.fromtimestamp(SCREEN_TIME_PNG.stat().st_mtime)
        screen_time_updated = mtime.date() == date.today()
        print(f"  Screen Time PNG: {'updated today' if screen_time_updated else f'last updated {mtime.date()}'}")

    # Build entry
    entry = {
        "date": today,
        "score": parsed.get("score", 0),
        "note": parsed.get("note", ""),
        "feedback": parsed.get("feedback", ""),
        "activitywatch": aw,
        "screen_time_updated": screen_time_updated
    }

    for key in ["business", "physique", "spirituel", "cognitif", "mental", "social"]:
        entry[key] = parsed.get(key, {})
        if not entry[key]:
            entry[key] = {"score": 0}

    # Update or append
    if existing_idx is not None:
        # Merge — preserve manually entered data
        old = data["days"][existing_idx]
        for k, v in entry.items():
            if isinstance(v, dict):
                existing_section = old.get(k, {})
                for field, val in v.items():
                    if val not in (None, 0, "", False) or field not in existing_section:
                        existing_section[field] = val
                old[k] = existing_section
            else:
                if v not in (None, 0, "", False) or k not in old:
                    old[k] = v
        data["days"][existing_idx] = old
        print(f"  Updated existing entry for {today}")
    else:
        data["days"].append(entry)
        print(f"  Added new entry for {today}")

    data["lastUpdated"] = today

    # Write
    with open(DATA_JSON, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  data.json updated.")
    return data


if __name__ == "__main__":
    update_data()
