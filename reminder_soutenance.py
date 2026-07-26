import subprocess, os

message = """🎓 RAPPEL SOUTENANCE — 9h30

Ta soutenance BUT3 (mémoire de stage) est à 9h30 dans la SALLE GRADINÉE.

Va directement salle gradinée. Ton tuteur ne vient pas (déjà confirmé à Yazid). Casse tout. 🔥"""

with open(os.path.expanduser('~/.claude/channels/telegram/.env')) as f:
    for line in f:
        if 'TELEGRAM_BOT_TOKEN' in line:
            token = line.strip().split('=', 1)[1].strip().strip('"')

chat_id = "5351269136"
url = f"https://api.telegram.org/bot{token}/sendMessage"
subprocess.run(['curl', '-s', '-X', 'POST', url,
    '--data-urlencode', f'text={message}',
    '-d', f'chat_id={chat_id}'], capture_output=True)

plist = os.path.expanduser('~/Library/LaunchAgents/com.shayan.reminder-soutenance.plist')
subprocess.run(['launchctl', 'unload', plist], capture_output=True)
try:
    os.remove(plist)
except OSError:
    pass
os.remove(__file__)
