#!/usr/bin/env python3
"""
JARVIS — Whoop collector
Pulls objective physiology from the WHOOP v2 API and merges it into data.json.

Whoop data REPLACES the manually declared fields it can cover:
  physique.coucher / lever / heures_sommeil / gym / gym_type
Everything Whoop cannot know (nutrition, deep work, Fajr, PMO...) stays manual.

Runs after collect.py so the objective numbers win over the DAILY LOG parse.

Usage:
  python3 whoop_collect.py            # last 30 days
  python3 whoop_collect.py --backfill # everything Whoop has
  python3 whoop_collect.py --days 90
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ENV_FILE = Path.home() / ".whoop.env"
TOKEN_FILE = Path.home() / ".whoop_tokens.json"
DATA_JSON = Path("/Users/shayanisse/jarvis-dashboard/data.json")

API = "https://api.prod.whoop.com"
# Cloudflare rejects the bare Python signature with error 1010 — a browser UA is required.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


# ── HTTP ──────────────────────────────────────────────────────────────

def curl(url, method="GET", token=None, form=None):
    cmd = ["curl", "-s", "--max-time", "30", "-X", method, url, "-H", f"User-Agent: {UA}"]
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]
    if form:
        cmd += ["-H", "Content-Type: application/x-www-form-urlencoded"]
        for k, v in form.items():
            cmd += ["--data-urlencode", f"{k}={v}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"curl failed: {r.stderr}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Whoop non-JSON response: {r.stdout[:200]}")


def load_env():
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def get_access_token():
    """Always refresh — access tokens live 1h. Whoop rotates the refresh token too."""
    env = load_env()
    tokens = json.loads(TOKEN_FILE.read_text())
    resp = curl(f"{API}/oauth/oauth2/token", method="POST", form={
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": env["WHOOP_CLIENT_ID"],
        "client_secret": env["WHOOP_CLIENT_SECRET"],
        "scope": "offline",
    })
    if "access_token" not in resp:
        raise RuntimeError(f"Refresh failed: {resp}")
    TOKEN_FILE.write_text(json.dumps(resp, indent=2))
    os.chmod(TOKEN_FILE, 0o600)
    return resp["access_token"]


def paginate(token, path, start_iso, limit=25):
    """Walk every page of a Whoop collection endpoint."""
    out, next_token = [], None
    while True:
        url = f"{API}/developer/v2/{path}?limit={limit}&start={start_iso}"
        if next_token:
            url += f"&nextToken={next_token}"
        page = curl(url, token=token)
        if "records" not in page:
            raise RuntimeError(f"{path}: {page}")
        out += page["records"]
        next_token = page.get("next_token")
        if not next_token:
            return out


# ── DATE HANDLING ─────────────────────────────────────────────────────

def local_dt(iso_utc, offset_str):
    """Whoop returns UTC + a separate '+04:00' offset. Convert to the wall clock Shayan lived."""
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    if offset_str:
        sign = 1 if offset_str[0] == "+" else -1
        h, m = int(offset_str[1:3]), int(offset_str[4:6])
        dt = dt.astimezone(timezone(sign * timedelta(hours=h, minutes=m)))
    return dt


def hm(dt):
    return dt.strftime("%H:%M")


# ── TRANSFORM ─────────────────────────────────────────────────────────

def build_days(sleeps, recoveries, cycles, workouts):
    """
    Anchor every metric on the WAKE date (local date the sleep ended).
    Cycles and recoveries are linked to that date via cycle_id, so a 03h30
    bedtime lands on the day it belongs to instead of splitting across two.
    """
    by_date = {}
    cycle_to_date = {}

    def slot(d):
        return by_date.setdefault(d, {})

    # 1. Sleep — the anchor
    for s in sleeps:
        if s.get("score_state") != "SCORED":
            continue
        # Naps were skipped entirely, yet Whoop counts them and subtracts them from the
        # night's sleep need. Filed on the day they happened, apart from the main sleep.
        if s.get("nap"):
            off = s.get("timezone_offset")
            n_start, n_end = local_dt(s["start"], off), local_dt(s["end"], off)
            n_st = s["score"]["stage_summary"]
            n_asleep = n_st["total_in_bed_time_milli"] - n_st["total_awake_time_milli"]
            slot(n_start.date().isoformat()).setdefault("siestes", []).append({
                "debut": hm(n_start),
                "fin": hm(n_end),
                "duree_h": round(n_asleep / 3_600_000, 2),
                "profond_h": round(n_st["total_slow_wave_sleep_time_milli"] / 3_600_000, 2),
                "rem_h": round(n_st["total_rem_sleep_time_milli"] / 3_600_000, 2),
            })
            continue
        off = s.get("timezone_offset")
        start, end = local_dt(s["start"], off), local_dt(s["end"], off)
        d = end.date().isoformat()
        sc = s["score"]
        st = sc["stage_summary"]
        asleep_ms = (st["total_in_bed_time_milli"] - st["total_awake_time_milli"])
        need = sc.get("sleep_needed", {})
        slot(d)["sleep"] = {
            "coucher": hm(start),
            "lever": hm(end),
            "heures_sommeil": round(asleep_ms / 3_600_000, 2),
            "heures_au_lit": round(st["total_in_bed_time_milli"] / 3_600_000, 2),
            "rem_h": round(st["total_rem_sleep_time_milli"] / 3_600_000, 2),
            "deep_h": round(st["total_slow_wave_sleep_time_milli"] / 3_600_000, 2),
            "light_h": round(st["total_light_sleep_time_milli"] / 3_600_000, 2),
            "awake_h": round(st["total_awake_time_milli"] / 3_600_000, 2),
            "cycles": st.get("sleep_cycle_count"),
            "perturbations": st.get("disturbance_count"),
            "performance_pct": sc.get("sleep_performance_percentage"),
            "efficiency_pct": round(sc["sleep_efficiency_percentage"], 1) if sc.get("sleep_efficiency_percentage") else None,
            "consistency_pct": sc.get("sleep_consistency_percentage"),
            "respiratory_rate": round(sc["respiratory_rate"], 1) if sc.get("respiratory_rate") else None,
            "dette_h": round(need.get("need_from_sleep_debt_milli", 0) / 3_600_000, 2),
            "besoin_h": round(sum(need.get(k, 0) or 0 for k in (
                "baseline_milli", "need_from_sleep_debt_milli",
                "need_from_recent_strain_milli", "need_from_recent_nap_milli")) / 3_600_000, 2),
            # The four terms Whoop adds up. Collapsing them hid why the need moved.
            "besoin_detail": {
                "base_h": round((need.get("baseline_milli") or 0) / 3_600_000, 2),
                "dette_h": round((need.get("need_from_sleep_debt_milli") or 0) / 3_600_000, 2),
                "strain_h": round((need.get("need_from_recent_strain_milli") or 0) / 3_600_000, 2),
                "siestes_h": round((need.get("need_from_recent_nap_milli") or 0) / 3_600_000, 2),
            },
        }
        if s.get("cycle_id"):
            cycle_to_date[s["cycle_id"]] = d

    # 2. Recovery — keyed by cycle
    for r in recoveries:
        if r.get("score_state") != "SCORED":
            continue
        d = cycle_to_date.get(r.get("cycle_id"))
        if not d:
            continue
        sc = r["score"]
        slot(d)["recovery"] = {
            "score": round(sc["recovery_score"]) if sc.get("recovery_score") is not None else None,
            "hrv": round(sc["hrv_rmssd_milli"], 1) if sc.get("hrv_rmssd_milli") else None,
            "rhr": round(sc["resting_heart_rate"]) if sc.get("resting_heart_rate") else None,
            "spo2": round(sc["spo2_percentage"], 1) if sc.get("spo2_percentage") else None,
            "temp_peau": round(sc["skin_temp_celsius"], 1) if sc.get("skin_temp_celsius") else None,
            "calibrating": sc.get("user_calibrating", False),
        }

    # 3. Cycle strain — also record each cycle's UTC span so workouts can be placed inside it
    spans = []
    for c in cycles:
        d = cycle_to_date.get(c["id"]) or local_dt(c["start"], c.get("timezone_offset")).date().isoformat()
        c_start = datetime.fromisoformat(c["start"].replace("Z", "+00:00"))
        c_end = (datetime.fromisoformat(c["end"].replace("Z", "+00:00"))
                 if c.get("end") else datetime.now(timezone.utc))
        spans.append((c_start, c_end, d))
        if c.get("score_state") != "SCORED":
            continue
        sc = c["score"]
        slot(d)["strain"] = {
            "jour": round(sc["strain"], 1) if sc.get("strain") is not None else None,
            "calories": round(sc["kilojoule"] / 4.184) if sc.get("kilojoule") else None,
            "fc_moyenne": sc.get("average_heart_rate"),
            "fc_max": sc.get("max_heart_rate"),
        }

    # 4. Workouts — placed in the Whoop cycle that contains them, not the civil day.
    # Shayan trains around 01h local, so a calendar-date split would file the session
    # under the following day and leave the day he actually trained showing zero.
    for w in workouts:
        if w.get("score_state") != "SCORED":
            continue
        off = w.get("timezone_offset")
        start, end = local_dt(w["start"], off), local_dt(w["end"], off)
        start_utc = datetime.fromisoformat(w["start"].replace("Z", "+00:00"))
        d = next((sd for cs, ce, sd in spans if cs <= start_utc <= ce), start.date().isoformat())
        sc = w.get("score") or {}
        slot(d).setdefault("workouts", []).append({
            "_utc": w["start"],
            "sport": w.get("sport_name") or "activity",
            "debut": hm(start),
            "duree_min": round((end - start).total_seconds() / 60),
            "strain": round(sc["strain"], 1) if sc.get("strain") is not None else None,
            "fc_moyenne": sc.get("average_heart_rate"),
            "fc_max": sc.get("max_heart_rate"),
            "calories": round(sc["kilojoule"] / 4.184) if sc.get("kilojoule") else None,
            # Six HR zones, in minutes. Two sessions of equal strain are not the same
            # session: this is what separates a walk from an actual set.
            "zones_min": [
                round((zd.get(k) or 0) / 60000, 1) for k in (
                    "zone_zero_milli", "zone_one_milli", "zone_two_milli",
                    "zone_three_milli", "zone_four_milli", "zone_five_milli")
            ] if (zd := sc.get("zone_durations") or {}) else None,
            "distance_m": round(sc["distance_meter"]) if sc.get("distance_meter") else None,
            "denivele_m": round(sc["altitude_gain_meter"]) if sc.get("altitude_gain_meter") else None,
            "pct_enregistre": round(sc["percent_recorded"] * 100) if sc.get("percent_recorded") else None,
        })

    # A Whoop cycle straddles midnight, so clock strings do not sort — order on the UTC stamp.
    for w in by_date.values():
        if w.get("workouts"):
            w["workouts"].sort(key=lambda x: x["_utc"])
            for x in w["workouts"]:
                del x["_utc"]

    return by_date


def baselines(by_date, n=30):
    """Rolling averages so a single day can be read against Shayan's own norm."""
    dates = sorted(by_date)[-n:]

    def avg(path):
        vals = []
        for d in dates:
            cur = by_date[d]
            for key in path:
                cur = (cur or {}).get(key) if isinstance(cur, dict) else None
            if isinstance(cur, (int, float)):
                vals.append(cur)
        return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "jours": len(dates),
        "recovery_moy": avg(["recovery", "score"]),
        "hrv_moy": avg(["recovery", "hrv"]),
        "rhr_moy": avg(["recovery", "rhr"]),
        "sommeil_moy_h": avg(["sleep", "heures_sommeil"]),
        "sleep_perf_moy": avg(["sleep", "performance_pct"]),
        "consistency_moy": avg(["sleep", "consistency_pct"]),
        "strain_moy": avg(["strain", "jour"]),
        "kcal_moy": avg(["strain", "calories"]),
        "profond_moy_h": avg(["sleep", "deep_h"]),
        "rem_moy_h": avg(["sleep", "rem_h"]),
        "perturbations_moy": avg(["sleep", "perturbations"]),
        "seances_total": sum(len(by_date[d].get("workouts") or []) for d in dates),
        "siestes_total": sum(len(by_date[d].get("siestes") or []) for d in dates),
        "jours_avec_seance": sum(1 for d in dates if by_date[d].get("workouts")),
    }


# ── SCORING ───────────────────────────────────────────────────────────
# Le pilier Physique vaut 20 points. Whoop en mesure 16 objectivement ;
# seule la nutrition reste déclarée au check-in du soir.
#
#   Sommeil vs besoin   5 pts   sleep.performance_pct
#   Recovery            4 pts   recovery.score, sur les paliers de Whoop
#   Régularité          2 pts   sleep.consistency_pct
#   Entraînement        5 pts   séance détectée + charge de la séance
#   Nutrition           4 pts   déclaré (goyslop)

PHYSIQUE_MAX = {"sommeil": 5, "recovery": 4, "regularite": 2, "entrainement": 5, "nutrition": 4}
NUTRITION_PTS = {"aucun": 4.0, "slip": 3.0, "modere": 1.5, "critique": 0.0}


def _band(v, paliers):
    """paliers = [(seuil, points), ...] du plus haut au plus bas."""
    for seuil, pts in paliers:
        if v >= seuil:
            return pts
    return 0.0


def score_physique(day):
    """Recalcule le pilier Physique. Ne note que ce qui est connu : une
    composante sans donnée reste absente du détail plutôt que de valoir zéro,
    sinon une journée non mesurée serait punie comme une mauvaise journée."""
    w = day.get("whoop") or {}
    rec = w.get("recovery") or {}
    slp = w.get("sleep") or {}
    wks = w.get("workouts") or []
    ph = day.setdefault("physique", {"score": 0})
    porte = bool(slp or rec)
    detail = {}

    if slp.get("performance_pct") is not None:
        detail["sommeil"] = round(min(5.0, slp["performance_pct"] / 100 * 5), 2)

    if rec.get("score") is not None:
        detail["recovery"] = _band(rec["score"], [(85, 4.0), (67, 3.5), (50, 2.5), (34, 1.5), (0, 0.5)])

    if slp.get("consistency_pct") is not None:
        detail["regularite"] = round(min(2.0, slp["consistency_pct"] / 100 * 2), 2)

    if wks:
        # Une séance vaut déjà la moitié des points ; le reste dépend de sa charge.
        charge = max((k.get("strain") or 0) for k in wks)
        detail["entrainement"] = round(min(5.0, 2.5 + _band(charge, [
            (12, 2.5), (9, 2.0), (6, 1.5), (3, 1.0), (0, 0.5)])), 2)
    elif porte:
        # Bracelet porté, aucune séance : c'est un vrai zéro, pas une donnée manquante.
        detail["entrainement"] = 0.0

    niveau = ph.get("goyslop_level")
    if niveau is None and ph.get("nutrition_clean") is not None:
        niveau = "aucun" if ph["nutrition_clean"] else "critique"
    if niveau in NUTRITION_PTS:
        detail["nutrition"] = NUTRITION_PTS[niveau]

    if not detail:
        return 0.0

    ph["score_detail"] = detail
    ph["score_manquant"] = sorted(k for k in PHYSIQUE_MAX if k not in detail)
    ph["score_dispo"] = sum(PHYSIQUE_MAX[k] for k in detail)
    ph["score_source"] = "whoop" if "nutrition" not in detail else "whoop+check-in"
    ph["score"] = round(sum(detail.values()), 1)
    return ph["score"]


def rescore(data):
    """Le total de la journée est la somme des piliers. Sans ce recalcul, le
    pilier Physique pouvait valoir 12 pendant que la journée affichait 0."""
    touched = 0
    for day in data.get("days", []):
        if not day.get("whoop"):
            continue
        score_physique(day)
        day["score"] = round(sum(
            (day.get(k) or {}).get("score") or 0
            for k in ("business", "physique", "spirituel", "cognitif", "mental", "social")
        ), 1)
        touched += 1
    return touched


# ── MERGE ─────────────────────────────────────────────────────────────

def merge(data, by_date):
    days = data.setdefault("days", [])
    index = {d["date"]: d for d in days}
    created = updated = 0

    for date_str in sorted(by_date):
        w = by_date[date_str]
        day = index.get(date_str)
        if day is None:
            day = {"date": date_str, "score": 0, "note": "", "feedback": ""}
            for k in ("business", "physique", "spirituel", "cognitif", "mental", "social"):
                day[k] = {"score": 0}
            days.append(day)
            index[date_str] = day
            created += 1
        else:
            updated += 1

        ph = day.setdefault("physique", {"score": 0})
        sleep = w.get("sleep")
        if sleep:
            # Objective data overwrites the declared values.
            ph["coucher"] = sleep["coucher"]
            ph["lever"] = sleep["lever"]
            ph["heures_sommeil"] = sleep["heures_sommeil"]
            ph["sommeil_source"] = "whoop"

        workouts = w.get("workouts") or []
        if workouts:
            ph["gym"] = True
            ph["gym_type"] = ", ".join(sorted({x["sport"] for x in workouts}))
            ph["gym_source"] = "whoop"
        elif "sleep" in w and ph.get("gym") is None:
            # Whoop was worn and logged nothing: that is a real "no session".
            ph["gym"] = False
            ph["gym_source"] = "whoop"

        day["whoop"] = {
            "recovery": w.get("recovery"),
            "sleep": sleep,
            "strain": w.get("strain"),
            "workouts": workouts,
            "siestes": w.get("siestes") or [],
        }

    days.sort(key=lambda d: d["date"])
    return created, updated


# ── MAIN ──────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if "--backfill" in args:
        days_back = 3650
    elif "--days" in args:
        days_back = int(args[args.index("--days") + 1])
    else:
        days_back = 30

    start_iso = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    print(f"[Whoop] fenêtre : {days_back} jours (depuis {start_iso[:10]})")

    token = get_access_token()
    print("[Whoop] token rafraîchi")

    profile = curl(f"{API}/developer/v2/user/profile/basic", token=token)
    body = curl(f"{API}/developer/v2/user/measurement/body", token=token)

    sleeps = paginate(token, "activity/sleep", start_iso)
    recoveries = paginate(token, "recovery", start_iso)
    cycles = paginate(token, "cycle", start_iso)
    workouts = paginate(token, "activity/workout", start_iso)
    print(f"[Whoop] {len(sleeps)} sommeils · {len(recoveries)} recoveries · "
          f"{len(cycles)} cycles · {len(workouts)} workouts")

    by_date = build_days(sleeps, recoveries, cycles, workouts)
    print(f"[Whoop] {len(by_date)} jours de physiologie")

    data = json.loads(DATA_JSON.read_text())
    created, updated = merge(data, by_date)
    scored = rescore(data)

    data["whoop"] = {
        "connected": True,
        "last_sync": datetime.now().isoformat(timespec="seconds"),
        "user": f"{profile.get('first_name','')} {profile.get('last_name','')}".strip(),
        "body": {
            "taille_m": body.get("height_meter"),
            "poids_kg": body.get("weight_kilogram"),
            "fc_max": body.get("max_heart_rate"),
        },
        "baselines": baselines(by_date),
        "jours_couverts": len(by_date),
        "premier_jour": min(by_date) if by_date else None,
    }

    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"[Whoop] data.json : {created} jours créés, {updated} mis à jour")
    print(f"[Whoop] pilier Physique recalculé sur {scored} jours")

    last = sorted(by_date)[-1] if by_date else None
    if last:
        w = by_date[last]
        rec = (w.get("recovery") or {}).get("score")
        slp = (w.get("sleep") or {}).get("heures_sommeil")
        stn = (w.get("strain") or {}).get("jour")
        print(f"[Whoop] dernier jour {last} — recovery {rec}% · sommeil {slp}h · strain {stn}")


if __name__ == "__main__":
    main()
