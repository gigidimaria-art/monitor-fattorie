import requests
import time
import json
from flask import Flask
import threading

TOKEN = 8748211671:AAGZdBWiB187vtQNQHBXtDf9Lg6aS4uDAi0
CHAT_ID = ""  # verrà riempito automaticamente al primo messaggio

URL_TELEGRAM = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
URL_BANDI = "https://www.sviluppocampania.it/bandi"

app = Flask(__name__)

def salva_ultimo_bando(titolo):
    with open("ultimo_bando.json", "w") as f:
        json.dump({"titolo": titolo}, f)

def leggi_ultimo_bando():
    try:
        with open("ultimo_bando.json", "r") as f:
            data = json.load(f)
            return data.get("titolo", "")
    except:
        return ""

def estrai_bando():
    try:
        r = requests.get(URL_BANDI, timeout=10)
        if r.status_code != 200:
            return None

        # Cerca un titolo di bando nella pagina
        testo = r.text.lower()

        # Qui puoi migliorare la ricerca, ma per ora cerchiamo parole chiave
        parole_chiave = ["bando", "avviso", "misura", "srd", "psr", "agricolo"]

        for parola in parole_chiave:
            if parola in testo:
                return f"Trovato riferimento a: {parola.upper()}"

        return None

    except Exception as e:
        print("Errore estrazione:", e)
        return None

def invia_messaggio(msg):
    global CHAT_ID
    if CHAT_ID == "":
        print("CHAT_ID non impostato, messaggio non inviato.")
        return

    try:
        requests.post(URL_TELEGRAM, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Errore invio messaggio:", e)

def ciclo_controllo():
    while True:
        print("Controllo nuovi bandi...")
        nuovo = estrai_bando()
        ultimo = leggi_ultimo_bando()

        if nuovo and nuovo != ultimo:
            salva_ultimo_bando(nuovo)
            invia_messaggio(f"🔔 Nuovo bando rilevato!\n\n{nuovo}")

        time.sleep(60)

@app.route("/", methods=["GET"])
def home():
    return "Bot attivo"

@app.route("/setchat/<cid>", methods=["GET"])
def set_chat(cid):
    global CHAT_ID
    CHAT_ID = cid
    return f"CHAT_ID impostato a {cid}"

def avvia_thread():
    t = threading.Thread(target=ciclo_controllo)
    t.daemon = True
    t.start()

if __name__ == "__main__":
    avvia_thread()
    app.run(host="0.0.0.0", port=10000)

