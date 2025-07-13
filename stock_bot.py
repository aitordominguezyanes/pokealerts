#!/usr/bin/env python3
"""
Scrapea LastLevel – Pokémon TCG.
Solo envía a n8n los productos cuyo estado cambia.
"""

import requests, json, os, sys, pathlib
from bs4 import BeautifulSoup

URL = (
    "https://www.lastlevel.es/distribucion/advanced_search_result.php?"
    "search_in_description=0&inc_subcat=1&keywords=pokemon+tcg"
)
HEADERS   = {"User-Agent": "Mozilla/5.0 (Mac)"}       # evita bloqueos
WEBHOOK   = os.environ["N8N_WEBHOOK"]                 # secreto GitHub
STATE_FILE = pathlib.Path("state.json")               # snapshot local

def scrape():
    html = requests.get(URL, headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for row in soup.select("table.productListing tr"):
        a = row.select_one("td:nth-of-type(2) a")
        if not a:
            continue
        name = a.get_text(strip=True)
        link = a["href"].split("?")[0]
        txt  = row.get_text().upper()
        state = (
            "Out" if any(w in txt for w in ("AGOTADO", "SIN STOCK", "OUT OF STOCK"))
            else "In" if "RESERV" in txt
            else None
        )
        if state:
            pid = link.split("-p-")[1].split(".")[0]
            items.append({"id": pid, "name": name, "link": link, "state": state})
    return items

def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}

def save_state(d):
    STATE_FILE.write_text(json.dumps(d))

def notify(product):
    # envía 1 JSON al Webhook de n8n
    requests.post(WEBHOOK, json=product, timeout=10)

def main():
    cur  = scrape()
    prev = load_state()
    next_state = {}
    for p in cur:
        next_state[p["id"]] = p["state"]
        if prev.get(p["id"]) != p["state"]:   # ← cambió
            notify(p)
    save_state(next_state)

if __name__ == "__main__":
    sys.exit(main())
