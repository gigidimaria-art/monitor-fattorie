import os
import time
import threading
from urllib.parse import urljoin, urlparse

import requests
import psycopg2
from flask import Flask, jsonify
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURAZIONE
# ============================================================

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
DATABASE_URL = os.environ.get("DATABASE_URL")

URL_TELEGRAM = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

URL_BANDI = "https://agricoltura.regione.campania.it/bandi.html"

app = Flask(__name__)


# ============================================================
# DATABASE
# ============================================================

def connessione_database():
    try:
        if not DATABASE_URL:
            print("DATABASE_URL non configurata")
            return None

        conn = psycopg2.connect(DATABASE_URL)
        return conn

    except Exception as e:
        print("Errore connessione database:", e)
        return None

def inizializza_database():

    conn = connessione_database()

    if not conn:
        return False

    try:

        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS bandi_monitoraggio (
                id SERIAL PRIMARY KEY,
                titolo TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                descrizione TEXT,
                impronta TEXT NOT NULL,
                prima_rilevazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultima_verifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cur.close()
        conn.close()

        print("✅ Database monitoraggio inizializzato")

        return True

    except Exception as e:

        print("Errore inizializzazione database:", e)

        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass

        return False

# ============================================================
# ESTRAZIONE BANDI
# ============================================================

def estrai_bandi_pagina(url):

    try:

        r = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 Monitoraggio-Bandi-Campania"
            }
        )

        r.raise_for_status()

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        risultati = []

        for riga in soup.find_all("tr"):

            celle = riga.find_all(
                ["td", "th"]
            )

            if len(celle) < 2:
                continue

            titolo = celle[0].get_text(
                " ",
                strip=True
            )

            scadenza = celle[1].get_text(
                " ",
                strip=True
            )

            link = riga.find(
                "a",
                href=True
            )

            if not link:
                continue

            url_bando = urljoin(
                url,
                link["href"]
            )

            if not titolo:
                continue

            descrizione = (
                f"{titolo} {scadenza}"
            ).strip()

            risultati.append(
                {
                    "titolo": titolo,
                    "url": url_bando,
                    "descrizione": descrizione
                }
            )

        return risultati

    except Exception as e:

        print(
            "Errore estrazione bandi:",
            e
        )

        return []


# ============================================================
# FILTRO BANDI RILEVANTI
# ============================================================

def bando_rilevante(bando):

    titolo = bando.get(
        "titolo",
        ""
    )

    descrizione = bando.get(
        "descrizione",
        ""
    )

    testo = (
        f"{titolo} {descrizione}"
    ).lower()

    testo = testo.replace(
        "-",
        " "
    )

    testo = testo.replace(
        "/",
        " "
    )

    testo = " ".join(
        testo.split()
    )

    if "fattoria didattica" in testo:
        return True

    if "fattorie didattiche" in testo:
        return True

    if (
        "srd03" in testo
        and "azione c" in testo
    ):
        return True

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
        termine in testo
        for termine in termini_base_didattica
    )

    contiene_didattica = any(
        termine in testo
        for termine in termini_didattici
    )

    if (
        contiene_base
        and contiene_didattica
    ):
        return True

    if (
        "aziende agricole" in testo
        and "sviluppo delle aree rurali" in testo
    ):
        return True

    if (
        "azienda agricola" in testo
        and "sviluppo delle aree rurali" in testo
    ):
        return True

    if (
        "azienda agricola" in testo
        and "fattoria" in testo
    ):
        return True

    if (
        "aziende agricole" in testo
        and "fattoria" in testo
    ):
        return True

    return False


# ============================================================
# VERIFICA INTEGRITÀ FONTE UFFICIALE
# ============================================================

def verifica_integrita_fonte():

    risultato = {
        "ok": False,
        "numero_bandi": 0,
        "srd03_trovato": False,
        "anomalie": [],
        "url_non_ufficiali": []
    }

    try:

        # ----------------------------------------------------
        # DEBUG 1 / DEBUG 2
        # ----------------------------------------------------

        print(
            "DEBUG 1 - prima della richiesta al sito"
        )

        response = requests.get(
            URL_BANDI,
            timeout=15,
            headers={
                "User-Agent":
                    "Mozilla/5.0 "
                    "Monitoraggio-Bandi-Campania"
            }
        )

        print(
            f"DEBUG 2 - risposta ricevuta: "
            f"HTTP {response.status_code}"
        )

        # ----------------------------------------------------
        # CONTROLLO HTTP
        # ----------------------------------------------------

        if response.status_code != 200:

            risultato["anomalie"].append(
                f"HTTP non valido: {response.status_code}"
            )

            return risultato

        # ----------------------------------------------------
        # CONTROLLO DIMENSIONE HTML
        # ----------------------------------------------------

        if len(response.text) < 5000:

            risultato["anomalie"].append(
                "Pagina HTML insolitamente piccola"
            )

        # ----------------------------------------------------
        # CONTROLLO CONTENUTO
        # ----------------------------------------------------

        testo = response.text.lower()

        parole_attese = [
            "bandi",
            "srd",
            "agricolt",
            "csr"
        ]

        parole_presenti = [
            parola
            for parola in parole_attese
            if parola in testo
        ]

        if len(parole_presenti) < 2:

            risultato["anomalie"].append(
                "Il contenuto della pagina non presenta "
                "sufficienti elementi attesi"
            )

        # ----------------------------------------------------
        # DEBUG 3 / DEBUG 4
        # ----------------------------------------------------

        print(
            "DEBUG 3 - prima dell'estrazione dei bandi"
        )

        bandi = estrai_bandi_pagina(
            URL_BANDI
        )

        print(
            f"DEBUG 4 - bandi estratti: "
            f"{len(bandi)}"
        )

        risultato["numero_bandi"] = len(
            bandi
        )

        if not bandi:

            risultato["anomalie"].append(
                "Nessun bando estratto dalla pagina"
            )

            return risultato

        # ----------------------------------------------------
        # CONTROLLO URL
        # ----------------------------------------------------

        dominio_ufficiale = (
            "agricoltura.regione.campania.it"
        )

        for bando in bandi:

            titolo = bando.get(
                "titolo",
                ""
            ).strip()

            url = bando.get(
                "url",
                ""
            ).strip()

            if not titolo:

                risultato["anomalie"].append(
                    "Trovato un elemento senza titolo"
                )

            if not url:

                risultato["anomalie"].append(
                    "Trovato un elemento senza URL"
                )

                continue

            parsed = urlparse(url)

            dominio = parsed.netloc.lower()

            if dominio != dominio_ufficiale:

                risultato[
                    "url_non_ufficiali"
                ].append(url)

        if risultato[
            "url_non_ufficiali"
        ]:

            risultato["anomalie"].append(
                "Sono stati trovati URL non appartenenti "
                "al dominio ufficiale"
            )

        # ----------------------------------------------------
        # RICERCA SRD03 AZIONE C
        # ----------------------------------------------------

        for bando in bandi:

            titolo = bando.get(
                "titolo",
                ""
            )

            descrizione = bando.get(
                "descrizione",
                ""
            )

            testo_bando = (
                f"{titolo} {descrizione}"
            ).lower()

            testo_bando = testo_bando.replace(
                "-",
                " "
            )

            testo_bando = " ".join(
                testo_bando.split()
            )

            if (
                "srd03" in testo_bando
                and "azione c" in testo_bando
            ):

                risultato[
                    "srd03_trovato"
                ] = True

                break

        if not risultato[
            "srd03_trovato"
        ]:

            risultato["anomalie"].append(
                "SRD03 - Azione C non trovato nella fonte"
            )

        # ----------------------------------------------------
        # RISULTATO FINALE
        # ----------------------------------------------------

        if not risultato["anomalie"]:

            risultato["ok"] = True

        return risultato

    except Exception as e:

        risultato["anomalie"].append(
            f"Errore durante il controllo della fonte: {e}"
        )

        return risultato


# ============================================================
# TELEGRAM
# ============================================================

def invia_messaggio(testo):

    try:

        if not TOKEN or not CHAT_ID:

            print(
                "TOKEN o CHAT_ID non configurati"
            )

            return False

        response = requests.post(
            URL_TELEGRAM,
            data={
                "chat_id": CHAT_ID,
                "text": testo
            },
            timeout=15
        )

        print(
            "Telegram HTTP:",
            response.status_code
        )

        if response.status_code == 200:

            print(
                "Messaggio Telegram inviato"
            )

            return True

        print(
            "Errore Telegram:",
            response.text
        )

        return False

    except Exception as e:

        print(
            "Errore invio Telegram:",
            e
        )

        return False


# ============================================================
# CICLO AUTOMATICO
# ============================================================

def ciclo_controllo():

    # Attende che Flask/Render abbia completato l'avvio
    time.sleep(15)

    while True:

        print("========================================", flush=True)
        print("CONTROLLO AUTOMATICO FONTE UFFICIALE", flush=True)
        print("========================================", flush=True)

        try:

            controllo = verifica_integrita_fonte()

            if controllo["ok"]:

                print("✅ FONTE OK", flush=True)

                print(
                    f"✅ Bandi estratti: "
                    f"{controllo['numero_bandi']}",
                    flush=True
                )

                print(
                    f"✅ SRD03 Azione C: "
                    f"{controllo['srd03_trovato']}",
                    flush=True
                )

            else:

                print("🔴 ANOMALIA FONTE", flush=True)

                for anomalia in controllo["anomalie"]:

                    print(
                        f"   ⚠️ {anomalia}",
                        flush=True
                    )

                if controllo["url_non_ufficiali"]:

                    print(
                        "   URL non ufficiali:",
                        flush=True
                    )

                    for url in controllo["url_non_ufficiali"]:

                        print(
                            f"      {url}",
                            flush=True
                        )

        except Exception as e:

            print(
                f"🔴 ERRORE CICLO AUTOMATICO: {e}",
                flush=True
            )

        print(
            "Attesa 60 secondi...",
            flush=True
        )

        time.sleep(60)


# ============================================================
# ROUTE PRINCIPALE
# ============================================================

@app.route("/")
def home():

    return jsonify(
        {
            "status": "online",
            "servizio": "Monitoraggio Bandi Campania"
        }
    )


# ============================================================
# ROUTE TEST BANDI
# ============================================================

@app.route("/testbandi")
def test_bandi():

    try:

        bandi = estrai_bandi_pagina(
            URL_BANDI
        )

        rilevanti = [
            bando
            for bando in bandi
            if bando_rilevante(bando)
        ]

        return jsonify(
            {
                "totale_bandi": len(bandi),
                "bandi_rilevanti": len(rilevanti),
                "risultati": rilevanti
            }
        )

    except Exception as e:

        return jsonify(
            {
                "errore": str(e)
            }
        ), 500


# ============================================================
# ROUTE VERIFICA FONTE
# ============================================================

@app.route("/verifica-fonte")
def verifica_fonte():

    risultato = verifica_integrita_fonte()

    return jsonify(
        risultato
    )


# ============================================================
# AVVIO
# ============================================================

if __name__ == "__main__":

    # Avvia il controllo automatico in background
    thread_monitor = threading.Thread(
        target=ciclo_controllo,
        daemon=True
    )

    thread_monitor.start()

    # Porta utilizzata da Render
    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
