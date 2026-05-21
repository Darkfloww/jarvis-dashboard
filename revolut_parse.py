#!/usr/bin/env python3
"""
Revolut CSV Parser for JARVIS
Usage: python3 revolut_parse.py path/to/revolut.csv
Updates data.json finance section with real monthly data
"""

import csv
import json
import sys
from datetime import datetime
from collections import defaultdict
from pathlib import Path

DATA_JSON = Path("/Users/shayanisse/jarvis-dashboard/data.json")

# These are not real income/expenses — pocket moves
POCKET_KEYWORDS = ['Pocket', 'Économies', 'Novaris', 'KL', 'Épargne']
RECHARGE_KEYWORDS = ['Recharge via']


def parse_revolut(filepath):
    rows = []
    with open(filepath, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    completed = [r for r in rows if r['État'] == 'TERMINÉ']

    # Current balance
    current_balance = float(completed[-1]['Solde']) if completed else 0

    # Monthly breakdown (real income/expenses only)
    months = defaultdict(lambda: {
        'revenus_total': 0,
        'depenses': 0,
        'flux_brut_entrant': 0,
        'flux_brut_sortant': 0,
        'nb_transactions': 0
    })

    for r in completed:
        try:
            date = datetime.strptime(r['Date de début'], '%Y-%m-%d %H:%M:%S')
            month = date.strftime('%Y-%m')
            amount = float(r['Montant'])
            desc = r.get('Description', '')

            months[month]['nb_transactions'] += 1

            is_pocket = any(k in desc for k in POCKET_KEYWORDS)
            is_recharge = any(k in desc for k in RECHARGE_KEYWORDS)

            if amount > 0:
                months[month]['flux_brut_entrant'] += amount
                if not is_pocket and not is_recharge:
                    months[month]['revenus_total'] += amount
            else:
                months[month]['flux_brut_sortant'] += abs(amount)
                if not is_pocket:
                    months[month]['depenses'] += abs(amount)

        except Exception:
            pass

    return current_balance, months


def update_data_json(balance, months):
    with open(DATA_JSON) as f:
        data = json.load(f)

    # Update patrimoine
    data['profile']['patrimoine'] = round(balance)

    # Build finance months list
    finance_months = []
    for month_str in sorted(months.keys()):
        m = months[month_str]
        finance_months.append({
            'month': month_str,
            'revenus_total': round(m['revenus_total']),
            'commissions_didier': 0,
            'commissions_closeGuard': 0,
            'commissions_kenzo': 0,
            'depenses': round(m['depenses']),
            'patrimoine_fin': 0,
            'nb_transactions': m['nb_transactions']
        })

    # Only keep last 12 months
    data['finance']['months'] = finance_months[-12:]

    with open(DATA_JSON, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"data.json updated. Patrimoine: {balance:.2f}€")
    print(f"Months updated: {len(finance_months[-12:])}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 revolut_parse.py path/to/revolut.csv")
        return

    filepath = sys.argv[1]
    balance, months = parse_revolut(filepath)

    print(f"\nSolde actuel : {balance:.2f}€")
    print(f"\n2026 — revenus réels / dépenses réelles :")
    for m in sorted(months.keys()):
        if '2026' in m:
            d = months[m]
            net = d['revenus_total'] - d['depenses']
            print(f"  {m}: +{d['revenus_total']:.0f}€ revenus | -{d['depenses']:.0f}€ dépenses | net {net:+.0f}€")

    update_data_json(balance, months)


if __name__ == '__main__':
    main()
