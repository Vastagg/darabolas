#!/usr/bin/env python3
"""Timárvasker árak letöltése a prices.json fájlba.

A GitHub Actions naponta futtatja (.github/workflows/arak.yml), de kézzel is
indítható:  python scripts/update_prices.py

Ha egy kategóriát nem sikerül beolvasni (pl. megváltozott az oldal), annak a
kategóriának a régi árait megtartja, így a program sosem marad ár nélkül.
"""
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE = "https://timarvasker.hu"
OUT = Path(__file__).resolve().parent.parent / "prices.json"

# (kategória kulcs a programban, oldal elérési út)
CATEGORIES = [
    ("zart", "/zartszelvenyek/k"),
    ("lapos", "/melegen-hengerelt-laposacel/k"),
    ("szog", "/szogacel/k"),
    ("lemez", "/melegen-hengerelt-vaslemez/k"),
    ("vasalat", "/forgaspontok-zsanerok/k"),
    ("vasalat", "/portalzarak/k"),
    ("vasalat", "/kilincsek/k"),
    ("vasalat", "/zsanerok/k"),
    ("vasalat", "/zartszelveny-dugok/k"),
    ("vasalat", "/kaputechnika/k"),
    ("vasalat", "/tolokapu/k"),
    ("vasalat", "/uszokapu/k"),
    ("vasalat", "/tolozarak/k"),
]

UNITS = ["szál", "fm", "kg", "db", "darab", "pár", "garn", "csomag", "tábla", "m2", "készlet", "szett"]
PRICE_RE = re.compile(r"(\d{1,3}(?:[   .]\d{3})+|\d+)\s*Ft", re.I)
UA = "Mozilla/5.0 (darabolas arfrissito; +https://github.com/Vastagg/darabolas)"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "hu"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def to_int(s):
    return int(re.sub(r"[^\d]", "", s))


def find_unit(text):
    t = text.lower()
    m = re.search(r"ft\s*/\s*([a-záéíóöőúüű0-9]+)", t)
    if m and m.group(1) in UNITS:
        return m.group(1)
    for u in UNITS:
        if re.search(r"(?<![a-záéíóöőúüű])" + re.escape(u) + r"(?![a-záéíóöőúüű])", t):
            return u
    return "db"


def product_id(href):
    m = re.search(r"/([^/]+)/t/?$", href)
    return m.group(1) if m else href


def parse(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    found = {}
    for a in soup.select('a[href]'):
        href = a.get("href", "")
        if not re.search(r"/t/?(\?.*)?$", href):
            continue
        url = urljoin(page_url, href.split("?")[0])
        pid = product_id(url)
        name = a.get_text(" ", strip=True) or a.get("title", "").strip()
        # A legközelebbi befoglaló elem, amelyben ár van, de csak ez az egy termék.
        node, block = a, None
        for _ in range(8):
            node = node.parent
            if node is None:
                break
            hrefs = {product_id(urljoin(page_url, x.get("href", "").split("?")[0]))
                     for x in node.select('a[href]') if re.search(r"/t/?(\?.*)?$", x.get("href", ""))}
            if len(hrefs) > 1:
                break
            if PRICE_RE.search(node.get_text(" ", strip=True)):
                block = node
                break
        if block is None:
            continue
        text = block.get_text(" ", strip=True)
        prices = [to_int(p) for p in PRICE_RE.findall(text)]
        prices = [p for p in prices if p > 0]
        if not prices:
            continue
        if not name:
            for x in block.select('a[href]'):
                if x.get_text(strip=True):
                    name = x.get_text(" ", strip=True)
                    break
        if not name:
            continue
        rec = found.get(pid)
        # Akciónál két ár is látszik: a kisebb az aktuális.
        price = min(prices)
        if rec is None or len(name) > len(rec["name"]):
            # a mértékegységet a név nélkül keressük (a névben gyakran ott a "6 fm")
            found[pid] = {"id": pid, "name": name, "price": price, "unit": find_unit(text.replace(name, " ")), "url": url}
    # további oldalak
    pages = set()
    for a in soup.select('a[href*="page="]'):
        pages.add(urljoin(page_url, a["href"]))
    return list(found.values()), pages


def scrape(cat, path):
    url = BASE + path
    seen, todo, out = set(), [url], {}
    while todo and len(seen) < 15:
        u = todo.pop(0)
        if u in seen:
            continue
        seen.add(u)
        html = get(u)
        items, pages = parse(html, u)
        for it in items:
            it["cat"] = cat
            out[it["id"]] = it
        todo += [p for p in pages if p not in seen and p.startswith(url.split("?")[0])]
        time.sleep(1)
    return list(out.values())


def main():
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text("utf-8"))
        except Exception:
            old = {}
    old_by_path = {}
    for p in old.get("products", []):
        old_by_path.setdefault(p.get("src", ""), []).append(p)

    products, report = {}, []
    for cat, path in CATEGORIES:
        try:
            items = scrape(cat, path)
        except Exception as e:  # hálózati hiba stb.
            items, err = [], str(e)
        else:
            err = ""
        if items:
            for it in items:
                it["src"] = path
                products.setdefault(it["id"], it)
            report.append(f"{path}: {len(items)} termék")
        else:
            kept = old_by_path.get(path, [])
            for it in kept:
                products.setdefault(it["id"], it)
            report.append(f"{path}: NEM SIKERÜLT ({err or 'nincs találat'}), {len(kept)} régi ár megtartva")

    print("\n".join(report))
    if len([p for p in products.values() if p["cat"] in ("zart", "lapos", "szog")]) < 20:
        print("Túl kevés szálanyag ár, a prices.json változatlan marad.")
        sys.exit(1)
    data = {
        "updated": datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),
        "source": BASE,
        "method": "automatikus",
        "note": "Bruttó (áfás) árak a Timárvasker webáruházából.",
        "products": sorted(products.values(), key=lambda p: (p["cat"], p["name"])),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=0).replace("\n{", "{"), "utf-8")
    print(f"{len(products)} termék mentve: {OUT}")


if __name__ == "__main__":
    main()
