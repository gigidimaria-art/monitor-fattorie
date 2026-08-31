def estrai_bando():
def leggi_ultimo_bando():
    try:
        with open("ultimo_bando.json", "r") as f:
            data = json.load(f)
            return data.get("titolo", "")
    except:
        return ""

def estrai_bando():  def estrai_bandi_pagina(url):
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
                # Cerca il testo dell'estratto
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
        return [] try:
        r = requests.get(URL_BANDI, timeout=10)
        if r.status_code != 200:
            return None

def estrai_bando():
def leggi_ultimo_bando():
    try:
        with open("ultimo_bando.json", "r") as f:
            data = json.load(f)
            return data.get("titolo", "")
    except:
        return ""

def estrai_bando():  def estrai_bandi_pagina(url):
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
                # Cerca il testo dell'estratto
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
        return [] try:
        r = requests.get(URL_BANDI, timeout=10)
        if r.status_code != 200:
            return None

