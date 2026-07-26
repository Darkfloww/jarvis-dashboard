import subprocess, os
message = "🎥 Rappel 3/3 — C'EST L'HEURE. Petronas allumées derrière toi. Tu tournes ta vidéo de prospection MAINTENANT. C'est ça qui te ramène un 2e client."
with open(os.path.expanduser('~/.claude/channels/telegram/.env')) as fh:
    for line in fh:
        if 'TELEGRAM_BOT_TOKEN' in line:
            token = line.strip().split('=',1)[1].strip().strip('"')
chat_id = "5351269136"
url = f"https://api.telegram.org/bot{token}/sendMessage"
subprocess.run(['curl','-s','-X','POST',url,'--data-urlencode',f'text={message}','-d',f'chat_id={chat_id}'], capture_output=True)
plist = os.path.expanduser('~/Library/LaunchAgents/com.shayan.reminder-prospec-3.plist')
subprocess.run(['launchctl','unload',plist], capture_output=True)
try: os.remove(plist)
except: pass
try: os.remove(__file__)
except: pass
