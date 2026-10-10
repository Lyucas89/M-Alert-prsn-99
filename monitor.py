import json
import os
import pathlib
import urllib.request

TOPIC = os.environ["NTFY_TOPIC"]
URLS = [u.strip() for u in os.environ["EVENT_URLS"].split(",") if u.strip()]
# Frasi che indicano "nessun biglietto". Le ultime tre sono ipotesi per FanSALE:
# si possono aggiungere/correggere con il secret EMPTY_MARKERS (separate da |).
SOLD_OUT = ("esaurito", "sold out", "nessuna offerta", "non ci sono offerte",
            "nessun biglietto") + tuple(
    m.strip().lower()
    for m in os.environ.get("EMPTY_MARKERS", "").split("|")
    if m.strip()
)
STATE_FILE = pathlib.Path("state.json")
UA = ("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36")


def notify(title, message, url=None, urgent=False):
    headers = {"Title": title, "Priority": "5" if urgent else "3"}
    if url:
        headers["Click"] = url
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}", data=message.encode("utf-8"), headers=headers
    )
    urllib.request.urlopen(req, timeout=20)


def check(url):
    """Restituisce (stato, dettaglio): esaurito / disponibile / errore."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9"}
        )
        html = urllib.request.urlopen(req, timeout=30).read()
        text = html.decode("utf-8", "ignore").lower()
    except Exception as e:
        return "errore", str(e)[:80]
    if "muse" not in text:
        return "errore", "pagina inattesa (bloccata o caricata via JavaScript?)"
    if any(marker in text for marker in SOLD_OUT):
        return "esaurito", ""
    return "disponibile", ""


def main():
    first_run = not STATE_FILE.exists()
    old = {} if first_run else json.loads(STATE_FILE.read_text())
    new, summary = {}, []

    for url in URLS:
        state, detail = check(url)
        new[url] = state
        summary.append(f"{state} {detail} - {url}".replace("  ", " "))
        if first_run:
            continue
        if state == "disponibile" and old.get(url) != "disponibile":
            notify("Muse Milano: biglietti disponibili!", "Corri su TicketOne", url, urgent=True)
        elif state == "errore" and old.get(url) != "errore":
            notify("Monitor Muse: pagina non leggibile", detail, url)

    if first_run:
        urgent = any(s == "disponibile" for s in new.values())
        notify("Monitor Muse attivo", "\n".join(summary), urgent=urgent)

    STATE_FILE.write_text(json.dumps(new, indent=1))
    print("\n".join(summary))


if __name__ == "__main__":
    main()
  
