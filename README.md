# Fém tervező

Offline is működő webes program (PWA) fém gyártmányok tervezéséhez.

- **Új munka** – kategória választása (kapu, kiskapu, kerítés, korlát, ablakrács, asztal, polc, egyedi), kérdések, javaslatok a korábbi munkák alapján.
- **Látványterv** – méretarányos rajz, egyszerű CAD-szerű szerkesztés (kijelölés, mozgatás, végpontok húzása, új rúd és lemez, törlés, visszavonás, nagyítás).
- **Korábbi munkák** – mentett és elfogadott tervek, biztonsági mentés fájlba.
- **Kosár** – tételenkénti és összes anyagköltség a Timárvasker árai alapján.
- **Darabolás** – szálanyag-optimalizálás gérvágással.

## Árak

A böngésző közvetlenül nem olvashatja a timarvasker.hu oldalt, ezért az árak a `prices.json` fájlban vannak.
A `.github/workflows/arak.yml` naponta lefuttatja a `scripts/update_prices.py` szkriptet, amely frissíti a fájlt.
Kézzel: GitHub → Actions → „Timárvasker árak frissítése” → Run workflow.

Online a program a legfrissebb `prices.json`-t tölti be, offline a legutolsó letöltöttel számol.
