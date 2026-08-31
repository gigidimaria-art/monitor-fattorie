import os
import time
import requests
from flask import Flask

# --- CONFIGURAZIONE ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- FUNZIONE INVIO MESSAGGIO ---
def invia_messaggio(testo):
    if not TOKEN or not CHAT_ID:
        print("⚠️ Variabili TELEGRAM_TOKEN o TELEGRAM_CHAT_ID non trovate.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": testo}
    try:
        requests.post(url, data=payload)
        print("✅ Messaggio inviato correttamente.")
    except Exception as e:
        print(f"❌ Errore nell'invio del messaggio: {e}")

# --- FUNZIONE PRINCIPALE ---
def monitor_bandi():
    while True:
        # Qui puoi inserire la tua logica di controllo bandi
        invia_messaggio("Bot attivo e in ascolto dei bandi...")
        time.sleep(3600)  # ogni ora

# --- SERVER FLASK PER RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot attivo su Render!"

if __name__ == "__main__":
    # Avvia il monitoraggio in background
    import threading
    t = threading.Thread(target=monitor_bandi)
    t.start()

    # Avvia il server Flask per mantenere la porta aperta
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
