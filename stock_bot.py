#!/usr/bin/env python3
"""
Scrapea LastLevel – Pokémon TCG.
• Recorre hasta 20 páginas de resultados.
• Elimina duplicados por id antes de procesar.
• Envía a n8n SOLAMENTE los productos cuyo estado cambia.
"""

import requests, json, os, sys, pathlib
from bs4 import BeautifulSoup

BASE_URL = (
    "https://www.lastlevel.es/distribucion/advanced_search_result.php"
    "?search_in_description=0&inc_subcat=1&keywords=pokemon+tcg"
)
HEADERS    = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
MAX_PAGES  = 20
WEBHOOK    = os.environ["N8N_WEBHOOK"]
STATE_FILE = pathlib.Path("state.json")


def scrape_all() -> list[dict]:
    """Devuelve la lista de productos únicos (id + estado)."""
    seen, all_items = set(), []

    for page in range(1, MAX_PAGES + 1):
        url = BASE_URL if page == 1 else f"{BASE_URL}&page={page}"
        html = requests.get(url, headers=HEADERS, timeout=20).text
        soup = BeautifulSoup(html, "html.parser")

        page_count = 0
        for prod in soup.select("div.product"):
            a = prod.select_one("h3.name a")
            if not a:
                continue

            link = a["href"].split("?")[0]
            pid  = link.split("-p-")[1].split(".")[0]
            if pid in seen:
                continue                       # duplicado; salta

            name = a.get_text(strip=True)
            txt  = (prod.select_one("button.checkout-page-button") or
                    prod).get_text(strip=True).upper()

            state = (
                "Out" if any(w in txt for w in ("AGOTADO", "SIN STOCK", "OUT OF STOCK"))
                else "In"  if any(w in txt for w in ("RESERV", "PREORDER"))
                else None
            )
            if state:
                seen.add(pid)
                all_items.append({"id": pid, "name": name, "link": link, "state": state})
                page_count += 1

        print(f"[DEBUG] página {page:02d}: {page_count} artículos")
        if page_count == 0:                     # fin real
            break

    print(f"[DEBUG] total artículos únicos: {len(all_items)}")
    return all_items


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(d: dict):
    STATE_FILE.write_text(json.dumps(d))


def notify(prod: dict):
    r = requests.post(WEBHOOK, json=prod, timeout=10)
    print("POST", r.status_code, prod["state"], prod["name"][:50])
    if r.status_code >= 400:
        print("[ERROR body]", r.text[:200])


def main():
    current   = scrape_all()
    prev      = load_state()
    next_snap = {}

    for p in current:
        next_snap[p["id"]] = p["state"]
        if prev.get(p["id"]) != p["state"]:    # cambió respecto al último run
            notify(p)

    save_state(next_snap)


if __name__ == "__main__":
    sys.exit(main())
