import os
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

URL = "https://regione.campania.it/regione/it/temi/agricoltura"
STATO_FILE = "ultimo_bando.json"


def manda_alert(messaggio):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": messaggio
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[ERRORE TELEGRAM] {e}")


def leggi_pagina(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[CONTROLLO] Errore di lettura per {url}: {e}")
        return None


def estrai_bando(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        titolo = soup.find("h2")
        if not titolo:
            return None
        return titolo.get_text(strip=True)
    except Exception as e:
        print(f"[ERRORE PARSING] {e}")
        return None


def leggi_stato():
    if not os.path.exists(STATO_FILE):
        return None
    try:
        with open(STATO_FILE, "r") as f:
            return json.load(f)
    except:
        return None


def salva_stato(bando):
    with open(STATO_FILE, "w") as f:
        json.dump({"bando": bando}, f)


def ciclo_controllo():
    while True:
        print("[INFO] Controllo in corso...")

        html = leggi_pagina(URL)
        if html:
            bando = estrai_bando(html)

            if bando:
                ultimo = leggi_stato()

                if not ultimo or ultimo["bando"] != bando:
                    print("[INFO] Nuovo bando trovato!")
                    salva_stato(bando)
                    manda_alert(f"🔔 NUOVO BANDO PUBBLICATO:\n\n{bando}")
                else:
                    print("[INFO] Nessun cambiamento.")
            else:
                print("[ATTENZIONE] Nessun bando trovato nella pagina.")
        else:
            print("[ATTENZIONE] Impossibile leggere la pagina.")

        time.sleep(600)


if __name__ == "__main__":
    manda_alert("🤖 Bot avviato correttamente su Render.")
    ciclo_controllo()
