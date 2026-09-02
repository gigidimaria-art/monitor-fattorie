import requests
import time
import json
from flask import Flask
import threading

import os
import psycopg2

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
DATABASE_URL = os.environ.get("DATABASE_URL")

def connessione_database():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print("Errore connessione database:", e)
        return None

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

        testo = r.text.lower()
        parole_chiave = ["bando", "avviso", "misura", "srd", "psr", "agricolo"]

        for parola in parole_chiave:
            if parola in testo:
                return f"Trovato riferimento a: {parola.upper()}"

        return None

    except Exception as e:
        print("Errore estrazione:", e)
        return None

def estrai_bandi_pagina(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(r.text, "html.parser")

        risultati = []

        # Cerca i titoli degli articoli presenti nella pagina
        titoli = soup.find_all("h2")

        for h2 in titoli:
            link = h2.find("a")

            if not link:
                continue

            titolo = link.get_text(" ", strip=True)
            url_bando = link.get("href")

            if not titolo or not url_bando:
                continue

            # Cerca il contenitore dell'articolo
            articolo = h2.find_parent("article")

            descrizione = ""

            if articolo:
                testo = articolo.get_text(" ", strip=True)
                descrizione = testo

            risultati.append({
                "titolo": titolo,
                "url": url_bando,
                "descrizione": descrizione
            })

        return risultati

    except Exception as e:
        print("Errore estrazione bandi:", e)
        return []
def bando_rilevante(bando):
    titolo = bando.get("titolo", "")
    descrizione = bando.get("descrizione", "")

    testo = f"{titolo} {descrizione}".lower()

    # Normalizza trattini, slash e spazi
    testo = testo.replace("-", " ")
    testo = testo.replace("/", " ")
    testo = " ".join(testo.split())

    # =========================================================
    # 1. CRITERI DIRETTI: sempre rilevanti
    # =========================================================

    if "fattoria didattica" in testo:
        return True

    if "fattorie didattiche" in testo:
        return True

    # SRD03 + Azione C
    # I due termini possono essere anche non consecutivi
    if "srd03" in testo and "azione c" in testo:
        return True

    # =========================================================
    # 2. AZIENDA/AGRICOLTURA + ATTIVITÀ DIDATTICHE/EDUCATIVE
    # =========================================================

    termini_base_didattica = [
        "agricoltura",
        "agricolo",
        "agricola",
        "agricoli",
        "agricole",
        "azienda agricola",
        "aziende agricole",
        "imprenditore agricolo",
        "imprenditori agricoli",
        "attività agricola",
        "attività agricole",
        "settore agricolo"
    ]

    termini_didattici = [
        "didattica",
        "didattico",
        "didattiche",
        "didattici",
        "educativa",
        "educativo",
        "educative",
        "educativi",
        "attività educative",
        "attività didattiche",
        "attività educative didattiche",
        "ludico didattico",
        "ludico didattica",
        "ludico didattiche",
        "ludico didattici"
    ]

    contiene_base = any(
        termine in testo for termine in termini_base_didattica
    )

    contiene_didattica = any(
        termine in testo for termine in termini_didattici
    )

    if contiene_base and contiene_didattica:
        return True

    # =========================================================
    # 3. AZIENDE AGRICOLE + SVILUPPO DELLE AREE RURALI
    # =========================================================

    if "aziende agricole" in testo and "sviluppo delle aree rurali" in testo:
        return True

    if "azienda agricola" in testo and "sviluppo delle aree rurali" in testo:
        return True

    # =========================================================
    # 4. AZIENDA AGRICOLA + FATTORIA
    # =========================================================

    if "azienda agricola" in testo and "fattoria" in testo:
        return True

    if "aziende agricole" in testo and "fattoria" in testo:
        return True

    return False

def invia_messaggio(msg):
    global CHAT_ID
    if CHAT_ID == "":
        print("CHAT_ID non impostato.")
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

@app.route("/test", methods=["GET"])
def test():
    invia_messaggio("🔧 Test eseguito: il bot sta funzionando correttamente!")
    return "Messaggio di test inviato."

def avvia_thread():
    t = threading.Thread(target=ciclo_controllo)
    t.daemon = True
    t.start()


@app.route("/testbandi", methods=["GET"])
def testbandi():
    risultati = estrai_bandi_pagina(URL_BANDI)

    if not risultati:
        return "NESSUN BANDO TROVATO"

    risposta = ""

    for bando in risultati:
        rilevante = bando_rilevante(bando)

        risposta += (
            f"RILEVANTE: {'SI' if rilevante else 'NO'}\n"
            f"Titolo: {bando['titolo']}\n"
            f"URL: {bando['url']}\n"
            f"Descrizione: {bando['descrizione']}\n"
            f"========================================\n"
        )

    return risposta


@app.route("/dbtest", methods=["GET"])
def dbtest():
    conn = connessione_database()

    if conn:
        conn.close()
        return "DATABASE OK - Connessione a Neon riuscita"

    return "DATABASE ERRORE - Connessione a Neon fallita"

@app.route("/dbinsert", methods=["GET"])
def dbinsert():
    conn = connessione_database()

    if not conn:
        return "DATABASE ERRORE - Connessione fallita"

    try:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO bandi (titolo, url, sito)
            VALUES (%s, %s, %s)
        """, (
            "TEST MONITORAGGIO FATTORIE",
            "https://www.sviluppocampania.it/bandi",
            "TEST"
        ))

        conn.commit()
        cur.close()
        conn.close()

        return "OK - Record di test inserito in Neon"

    except Exception as e:
        conn.rollback()
        conn.close()
        return f"ERRORE INSERIMENTO: {e}"

if __name__ == "__main__":
    avvia_thread()
    app.run(host="0.0.0.0", port=10000)
