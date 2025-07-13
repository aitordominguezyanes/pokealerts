#!/usr/bin/env python3
"""
Scrapea LastLevel – Pokémon TCG y envía SOLO los productos cuyo estado
cambia al Webhook de n8n (que luego reenvía a Discord).
"""

import requests, json, os, sys, pathlib
from bs4 import BeautifulSoup

URL = (
    "https://www.lastlevel.es/distribucion/advanced_search_result.php?"
    "search_in_description=0&inc_subcat=1&keywords=pokemon+tcg"
)
HEADERS    = {"User-Agent": "Mozilla/5.0 (Mac)"}   # evita bloqueos
WEBHOOK    = os.environ["N8N_WEBHOOK"]             # secreto GitHub
STATE_FILE = pathlib.Path("state.json")            # snapshot local


def scrape() -> list[dict]:
    print("→ solicitando", URL)                    # DEBUG
    html = requests.get(URL, headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []

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

    print("[DEBUG] productos encontrados:", len(items))      # DEBUG
    if items:
        print("[DEBUG] primer item:", items[0])              # DEBUG
    return items


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(d: dict):
    STATE_FILE.write_text(json.dumps(d))


def notify(product: dict):
    r = requests.post(WEBHOOK, json=product, timeout=10)
    print("POST", r.status_code, product["name"])            # DEBUG
    if r.status_code >= 400:
        print("[ERROR body]", r.text[:200])


def main():
    try:
        current = scrape()
    except Exception as e:                                    # DEBUG
        print("[ERROR scrape]", e)
        raise

    prev = load_state()
    next_state = {}

    for p in current:
        next_state[p["id"]] = p["state"]
        if prev.get(p["id"]) != p["state"]:
            notify(p)

    save_state(next_state)


if __name__ == "__main__":
    sys.exit(main())
