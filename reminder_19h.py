import subprocess, os

message = """Rappel 19h00 :

1. Email Elodie LEGROS (BUT 3 TC) : envoie ton attestation de responsabilité civile (renouvellement). Sans ce doc, pas de séminaire la semaine prochaine.

2. Demande d'évaluation de stage : remplis le formulaire que ton prof (Zid Alibay) a envoyé à Adrien Marquis."""

with open(os.path.expanduser('~/.claude/channels/telegram/.env')) as f:
    for line in f:
        if 'TELEGRAM_BOT_TOKEN' in line:
            token = line.strip().split('=',1)[1].strip().strip('"')

chat_id = "5351269136"
url = f"https://api.telegram.org/bot{token}/sendMessage"
subprocess.run(['curl', '-s', '-X', 'POST', url,
    '--data-urlencode', f'text={message}',
    '-d', f'chat_id={chat_id}'], capture_output=True)

plist = os.path.expanduser('~/Library/LaunchAgents/com.shayan.reminder-19h.plist')
subprocess.run(['launchctl', 'unload', plist], capture_output=True)
os.remove(plist)
os.remove(__file__)
