"""Modelle in der Oberfläche anzeigen und wechseln (10.10.2026).

Sprachmodelle und Antwortsprache wechseln sofort. Das Embedding nur nach Bestätigung: ein
anderes Embedding macht alle gespeicherten Vektoren ungültig (index.py, _GUELTIGES_EMBEDDING),
bis zum Neu-Einbetten findet die Suche weniger. Deshalb startet nach dem Wechsel sofort ein
Einlese-Lauf, der nur die Vektoren neu bildet.

Die Wahl wird in modelle.yaml geschrieben — zeilenweise, damit die Messkommentare dort stehen
bleiben — und gilt damit auch nach einem Neustart.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from dokumentenassistent.typen import DokumentenassistentFehler

router = APIRouter()

WAEHLBAR = ("llm", "llm_suche", "embedding", "sprache")


def anzeige(werkstatt) -> list[tuple[str, str]]:
    """Was dieser Bestand gerade wirklich benutzt — aus den geladenen Objekten, nicht aus der Datei."""
    p, ps = werkstatt.provider, getattr(werkstatt, "provider_suche", None)
    e = getattr(werkstatt, "sucheinstellungen", None)
    llm = getattr(p, "llm_modell", "unbekannt")
    return [("Sprachmodell (Einordnen)", llm),
            ("Sprachmodell (Antworten)", getattr(ps, "llm_modell", llm) if ps else llm),
            ("Embedding", getattr(p, "embed_modell", "unbekannt")),
            ("Reranker", getattr(getattr(e, "reranker", None), "modell_name", "keiner")),
            ("Laufzeit", "LM Studio" if type(p).__name__ == "LmStudioProvider" else "Ollama"),
            ("Antwortsprache", getattr(p, "sprache", "Deutsch"))]


def _liste(url: str, schluessel: str, feld: str) -> list[str]:
    try:
        with urllib.request.urlopen(url, timeout=1) as antwort:
            daten = json.loads(antwort.read())
    except (OSError, ValueError):
        return []
    return sorted(m.get(feld, "") for m in daten.get(schluessel, []) if m.get(feld))


def verfuegbar(werkstatt) -> dict[str, list[str]]:
    """Installierte Modelle: Embeddings immer aus Ollama, Sprachmodelle aus der eingestellten Laufzeit.
    Leere Liste = Laufzeit nicht erreichbar; die Oberfläche zeigt dann nur das aktuelle Modell."""
    p = werkstatt.provider
    ollama = _liste(p.host + "/api/tags", "models", "name")
    if type(p).__name__ == "LmStudioProvider":
        sprachmodelle = _liste(p.llm_host + "/v1/models", "data", "id")
    else:
        sprachmodelle = [m for m in ollama if "embed" not in m]
    return {"sprachmodelle": sprachmodelle, "embeddings": [m for m in ollama if "embed" in m]}


def fundstellen_anzahl(werkstatt) -> int:
    return werkstatt.index._eine("SELECT COUNT(*) FROM fundstellen")[0]


def schreibe(pfad: Path, werte: dict[str, str]) -> None:
    """Setzt `schluessel: wert` in modelle.yaml. Kommentare und Reihenfolge bleiben erhalten;
    ein fehlender Schlüssel (z.B. llm_suche) wird nach `llm:` eingefügt."""
    zeilen = pfad.read_text().splitlines()
    for schluessel, wert in werte.items():
        muster = re.compile(rf"^{schluessel}:\s*[^#\n]*?(\s+#.*)?$")
        treffer = [i for i, z in enumerate(zeilen) if muster.match(z)]
        if treffer:
            kommentar = muster.match(zeilen[treffer[0]]).group(1) or ""
            zeilen[treffer[0]] = f"{schluessel}: {wert}{kommentar}"
        else:
            nach = next((i for i, z in enumerate(zeilen) if z.startswith("llm:")), len(zeilen) - 1)
            zeilen.insert(nach + 1, f"{schluessel}: {wert}")
    pfad.write_text("\n".join(zeilen) + "\n")


@router.post("/modelle")
def modelle_wechseln(
    request: Request,
    llm: str = Form(...),
    llm_suche: str = Form(...),
    embedding: str = Form(...),
    sprache: str = Form(...),
    embedding_bestaetigt: str = Form(""),
    zurueck: str = Form("/profil"),
) -> RedirectResponse:
    from dokumentenassistent import web  # spät: web bindet diesen Router ein

    werkstatt = request.app.state.werkstatt
    if werkstatt is None:
        return web._zurueck("/start", "Erst einen Bestand öffnen.")
    ziel = zurueck if zurueck.startswith("/") else "/profil"
    if request.app.state.job.laeuft:
        return web._zurueck(ziel, "Während ein Durchgang läuft, bleiben die Modelle, wie sie sind.")
    werte = {k: v.strip() for k, v in
             dict(llm=llm, llm_suche=llm_suche, embedding=embedding, sprache=sprache).items()}
    if not all(werte.values()):
        return web._zurueck(ziel, "Jedes Feld braucht einen Wert.")
    embedding_neu = werte["embedding"] != werkstatt.provider.embed_modell
    if embedding_neu and embedding_bestaetigt != "ja":
        return web._zurueck(ziel, "Embedding nicht gewechselt: der Wechsel muss bestätigt werden.")

    pfad = request.app.state.modelle_pfad
    vorher = pfad.read_text()
    schreibe(pfad, werte)
    try:
        werkstatt.provider = request.app.state.provider_laden()
        werkstatt.provider_suche = request.app.state.provider_suche_laden()
    except DokumentenassistentFehler as fehler:
        pfad.write_text(vorher)  # nichts halb umgestellt lassen
        return web._zurueck(ziel, f"Modelle nicht gewechselt: {fehler}")

    if embedding_neu:
        web._job_starten(request, werkstatt, phase="auslesen")
        return web._zurueck("/profil", f"Embedding auf {werte['embedding']} gewechselt. "
                                       "Die Vektoren werden jetzt neu gebildet.")
    return web._zurueck(ziel, "Modelle gewechselt. Sie gelten ab der nächsten Anfrage.")
