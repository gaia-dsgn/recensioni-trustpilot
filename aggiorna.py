"""Copia le recensioni Trustpilot di andrei-copy.com in recensioni.json.

Gira ogni 6 ore su GitHub Actions (.github/workflows/aggiorna.yml).
I blocchi di andrei-copy.com leggono il file da GitHub Pages:
https://gaia-dsgn.github.io/recensioni-trustpilot/recensioni.json
"""
import json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

QUI = Path(__file__).parent
URL = "https://www.trustpilot.com/review/andrei-copy.com?languages=all&sort=recency&page={}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

# Recensioni nuove: prodotto dedotto solo da nomi espliciti. Nessun nome -> "altro".
# Per correggere una recensione a mano, aggiungila a prodotti.json.
PAROLE = {
    "cmp": r"copywriting mentorship|copy mentorship|\bcmp\b|\bcm ?4\b",
    "fo": r"funnel ?operator|\bfunops\b",
    "speedrun": r"speedrun",
    "pmo": r"programma operativo",
    "v101": r"vendita ?101|\bv101\b",
}
NOMI = {"cliente": "Cliente Trustpilot"}


def pagina(pg, n):
    for tentativo in range(3):
        try:
            pg.goto(URL.format(n), wait_until="domcontentloaded", timeout=60000)
            # la pagina di verifica AWS WAF si ricarica da sola: aspetta quella vera
            for _ in range(45):
                try:
                    if pg.locator("#__NEXT_DATA__").count():
                        return json.loads(pg.locator("#__NEXT_DATA__").inner_text())["props"]["pageProps"]
                except Exception:
                    pass  # contesto distrutto dal ricaricamento: riprova
                time.sleep(1)
        except Exception as e:
            print(f"pagina {n}, tentativo {tentativo + 1}: {e}", file=sys.stderr)
        time.sleep(5 * (tentativo + 1))
    raise RuntimeError(f"pagina {n}: Trustpilot non ha risposto")


def scarica():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(locale="it-IT", user_agent=UA)
        prima = pagina(pg, 1)
        info = prima["businessUnit"]
        pagine = prima["filters"]["pagination"]["totalPages"]
        attese = prima["filters"]["pagination"]["totalCount"]
        grezze = list(prima["reviews"])
        for n in range(2, pagine + 1):
            grezze += pagina(pg, n)["reviews"]
        b.close()
    viste, uniche = set(), []
    for r in grezze:
        if r["id"] not in viste:
            viste.add(r["id"])
            uniche.append(r)
    if len(uniche) < attese:
        raise RuntimeError(f"lette {len(uniche)} recensioni su {attese}: non sovrascrivo")
    return info, uniche


def nome(s):
    s = re.sub(r"\s+", " ", s).strip()
    if s.lower() in NOMI:
        return NOMI[s.lower()]
    return s.title() if s == s.lower() else s


def prodotti(r, manuali):
    if r["id"] in manuali:
        return manuali[r["id"]]["p"]
    testo = (r.get("title") or "") + " " + (r.get("text") or "")
    trovati = [k for k, rx in PAROLE.items() if re.search(rx, testo, re.I)]
    return trovati or ["altro"]


def main():
    manuali = json.loads((QUI / "prodotti.json").read_text())["recensioni"]
    info, grezze = scarica()
    out = []
    for r in grezze:
        out.append({
            "id": r["id"],
            "n": nome(r["consumer"]["displayName"]),
            "r": r["rating"],
            "titolo": re.sub(r"\s+", " ", r.get("title") or "").strip(),
            "t": re.sub(r"\s+", " ", r.get("text") or "").strip(),
            "data": r["dates"]["publishedDate"],
            "p": prodotti(r, manuali),
        })
    out.sort(key=lambda x: x["data"], reverse=True)
    dati = {
        "trustpilot": {
            "punteggio": info.get("trustScore"),
            "totale": info.get("numberOfReviews"),
            "url": "https://www.trustpilot.com/review/andrei-copy.com",
        },
        "recensioni": out,
    }
    f = QUI / "recensioni.json"
    vecchio = json.loads(f.read_text()) if f.exists() else {}
    vecchio.pop("aggiornato", None)
    if vecchio == dati:
        print("nessuna novita'")
        return
    dati = {"aggiornato": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **dati}
    f.write_text(json.dumps(dati, ensure_ascii=False, indent=1) + "\n")
    print(f"scritte {len(out)} recensioni")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERRORE:", e, file=sys.stderr)
        sys.exit(1)
