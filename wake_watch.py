#!/usr/bin/env python3
"""
JARVIS — Wake Watch

Déclenche le brief du matin au réveil réel de Shayan, pas à une heure fixe.

Pourquoi : son lever va de 09h49 à 15h38. Un brief à 8h30 tombait avant le
réveil, donc sans la nuit qui venait de se terminer. La Whoop sait exactement
quand il s'endort et se réveille ; on attend que le sommeil principal de la
nuit soit publié et scoré, puis on envoie.

Mécanique :
  1. tourne toutes les 10 minutes (launchd StartInterval, aucune heure locale
     dans le plist, voir l'historique des bascules de fuseau)
  2. cherche le dernier sommeil SCORED non-sieste
  3. s'il est plus récent que celui du dernier brief, relance le collecteur
     puis envoie le brief, et mémorise
  4. sinon sort en silence

Garde-fou : au-delà de FENETRE_H heures après le réveil, on n'envoie plus.
Sinon un Mac resté éteint deux jours enverrait un brief périmé au rallumage.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path("/Users/shayanisse/jarvis-dashboard")
STATE = Path.home() / ".jarvis_wake_state.json"
PY = "/usr/bin/python3"
FENETRE_H = 8

sys.path.insert(0, str(BASE))
import whoop_collect as wc  # noqa: E402  (auth, curl et pagination déjà écrits ici)


def log(msg):
    print(f"[wake {datetime.now():%Y-%m-%d %H:%M}] {msg}", flush=True)


def charger_etat():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def dernier_reveil(token):
    """Dernier sommeil principal scoré, avec son heure de fin locale."""
    depuis = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    sommeils = wc.paginate(token, "activity/sleep", depuis)
    principaux = [s for s in sommeils
                  if s.get("score_state") == "SCORED" and not s.get("nap")]
    if not principaux:
        return None
    return max(principaux, key=lambda s: s["end"])


def main():
    forcer = "--force" in sys.argv
    etat = charger_etat()

    try:
        token = wc.get_access_token()
    except Exception as e:
        log(f"token Whoop indisponible : {e}")
        return 1

    sommeil = dernier_reveil(token)
    if not sommeil:
        log("aucun sommeil scoré sur 3 jours")
        return 0

    fin = sommeil["end"]
    if fin == etat.get("dernier_sommeil") and not forcer:
        return 0  # déjà briefé sur cette nuit

    reveil = wc.local_dt(fin, sommeil.get("timezone_offset"))
    ecoule = (datetime.now(reveil.tzinfo) - reveil).total_seconds() / 3600
    if ecoule > FENETRE_H and not forcer:
        log(f"réveil à {wc.hm(reveil)} il y a {ecoule:.1f} h, hors fenêtre : pas de brief")
        json.dump({"dernier_sommeil": fin, "envoye": False, "raison": "hors fenetre"},
                  STATE.open("w"))
        return 0

    # La nuit doit être dans data.json avant que le brief la lise.
    log(f"réveil détecté à {wc.hm(reveil)}, collecte puis brief")
    r = subprocess.run([PY, str(BASE / "whoop_collect.py"), "--days", "7"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        log(f"collecteur en échec : {r.stderr[-300:]}")
        return 1

    r = subprocess.run([PY, str(BASE / "morning_brief.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        log(f"brief en échec : {r.stderr[-300:]}")
        return 1

    json.dump({"dernier_sommeil": fin, "reveil_local": reveil.isoformat(),
               "envoye_le": datetime.now().isoformat(timespec="seconds")},
              STATE.open("w"))
    log("brief envoyé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
