#!/usr/bin/env python3
"""
Scrapea LastLevel – Pokémon TCG.
Navega hasta 20 páginas como máximo y sólo envía a n8n los productos
cuyo estado cambió.
"""

import requests, json, os, sys, pathlib
from bs4 import BeautifulSoup

BASE_URL = (
    "https://www.lastlevel.es/distribucion/advanced_search_result.php"
    "?search_in_description=0&inc_subcat=1&keywords=pokemon+tcg"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}
MAX_PAGES  = 20                               # ← cortafuegos infinito
WEBHOOK    = os.environ["N8N_WEBHOOK"]
STATE_FILE = pathlib.Path("state.json")


def scrape_page(url: str) -> list[dict]:
    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")
    items: list[dict] = []

    for prod in soup.select("div.product"):
        a = prod.select_one("h3.name a")
        if not a:
            continue
        name = a.get_text(strip=True)
        link = a["href"].split("?")[0]
        txt  = (prod.select_one("button.checkout-page-button") or
                prod).get_text(strip=True).upper()

        state = (
            "Out" if any(w in txt for w in ("AGOTADO", "SIN STOCK", "OUT OF STOCK"))
            else "In"  if any(w in txt for w in ("RESERV", "PREORDER"))
            else None
        )
        if state:
            pid = link.split("-p-")[1].split(".")[0]
            items.append({"id": pid, "name": name, "link": link, "state": state})
    return items


def scrape_all() -> list[dict]:
    all_items = []
    for page in range(1, MAX_PAGES + 1):
        url   = BASE_URL if page == 1 else f"{BASE_URL}&page={page}"
        items = scrape_page(url)
        print(f"[DEBUG] página {page:02d}: {len(items)} artículos")
        if not items:
            break
        all_items.extend(items)
    print("[DEBUG] total artículos:", len(all_items))
    return all_items


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(d: dict):
    STATE_FILE.write_text(json.dumps(d))


def notify(prod: dict):
    r = requests.post(WEBHOOK, json=prod, timeout=10)
    print("POST", r.status_code, prod["name"])
    if r.status_code >= 400:
        print("[ERROR body]", r.text[:200])


def main():
    current = scrape_all()
    prev, next_state = load_state(), {}

    for p in current:
        next_state[p["id"]] = p["state"]
        if prev.get(p["id"]) != p["state"]:
            notify(p)

    save_state(next_state)


if __name__ == "__main__":
    sys.exit(main())
