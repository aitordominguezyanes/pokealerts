#!/usr/bin/env python3
"""
Avisador de stock LastLevel (Pokémon TCG).
Scrapea la web, guarda state.json y envía a n8n sólo cambios de estado.
"""
import requests, json, os, sys, pathlib
from bs4 import BeautifulSoup

URL = (
    "https://www.lastlevel.es/distribucion/advanced_search_result.php?"
    "search_in_description=0&inc_subcat=1&keywords=pokemon+tcg"
)
WEBHOOK    = os.environ["N8N_WEBHOOK"]           # → lo inyectará Actions
STATE_FILE = pathlib.Path("state.json")

def scrape():
    html = requests.get(URL, timeout=20).text
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
            "Out" if any(w in txt for w in ("AGOTADO","SIN STOCK","OUT OF STOCK"))
            else "In" if "RESERV" in txt
            else None
        )
        if state:
            pid = link.split("-p-")[1].split(".")[0]
            items.append({"id": pid, "name": name, "link": link, "state": state})
    return items

def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}

def save_state(data):
    STATE_FILE.write_text(json.dumps(data))

def notify(prod):
    requests.post(WEBHOOK, json=prod, timeout=10)

def main():
    cur  = scrape()
    prev = load_state()
    next_state = {}
    for p in cur:
        next_state[p["id"]] = p["state"]
        if prev.get(p["id"]) != p["state"]:
            notify(p)
    save_state(next_state)

if __name__ == "__main__":
    sys.exit(main())
