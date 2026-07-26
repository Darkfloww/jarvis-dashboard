import subprocess, os
message = "🎥 Rappel 1/3 — Aujourd'hui tu tournes ta vidéo de prospection CE SOIR (Airbnb, vue Petronas). Cet aprem : prépare ton script + le cadrage. Zéro excuse."
with open(os.path.expanduser('~/.claude/channels/telegram/.env')) as fh:
    for line in fh:
        if 'TELEGRAM_BOT_TOKEN' in line:
            token = line.strip().split('=',1)[1].strip().strip('"')
chat_id = "5351269136"
url = f"https://api.telegram.org/bot{token}/sendMessage"
subprocess.run(['curl','-s','-X','POST',url,'--data-urlencode',f'text={message}','-d',f'chat_id={chat_id}'], capture_output=True)
plist = os.path.expanduser('~/Library/LaunchAgents/com.shayan.reminder-prospec-1.plist')
subprocess.run(['launchctl','unload',plist], capture_output=True)
try: os.remove(plist)
except: pass
try: os.remove(__file__)
except: pass
