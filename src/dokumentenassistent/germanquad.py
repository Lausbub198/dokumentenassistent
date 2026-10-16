"""GermanQuAD als zweiter, UNABHÄNGIGER Prüfstein für das Retrieval-Eval.

Anlass (22.09.2026): der bisherige Goldstandard `beispiele/malerbetrieb` ist **synthetisch** —
Dokumente und Fragen stammen aus derselben Quelle (`beispiele/malerbetrieb/README.md`:
„Alles frei erfunden", erzeugt von `erzeugen.py`/`texte.py` am 19.09.). Wer die Frage schreibt
und den Text schreibt, den die Frage treffen soll, misst am Ende die eigene Wortwahl mit.
Alle Retrieval-Zahlen dieser Woche (`docs/retrieval-befund-2026-09-21.md`) tragen damit
maximalen Autorenschafts-Bias. GermanQuAD schließt genau diese Lücke: **Fragen UND Texte
stammen von Dritten** — deutsche Wikipedia-Absätze, Fragen von menschlichen Annotatoren
(deepset/germanquad, CC-BY-4.0; hier der MTEB-Spiegel, siehe `beweise/germanquad/README.md`).

**Kein Chunking.** Der Korpus liefert bereits Absätze: je Zeile ein Wikipedia-Abschnitt, und
genau dieser Abschnitt ist die Antwortstelle der zugehörigen Frage. Würde dieses Modul die
Texte erneut durch `fundstellen.zerlege` schicken, entstünden mehrere Fundstellen je
Korpuszeile — die Soll-ID träfe dann keine davon mehr eindeutig, und der absatzgenaue Treffer
(der Vorteil dieses Korpus gegenüber malerbetrieb) wäre verloren. Eine Korpuszeile = eine
`Fundstelle`, `seite=1`, `absatz=1`.

`pyarrow` ist optional (`[project.optional-dependencies] eval`) und wird erst beim Laden
importiert, damit `uv run pytest` ohne das Extra nicht am Import dieses Moduls scheitert.
"""
from __future__ import annotations

import random
from pathlib import Path

from dokumentenassistent.typen import DokumentenassistentFehler, Fundstelle

STANDARD_ORDNER = Path("beweise/germanquad")
DATEIEN = ("corpus.arrow", "queries.arrow", "qrels.arrow")


class GermanQuadFehler(DokumentenassistentFehler):
    """Fehlende Arrow-Datei, fehlendes pyarrow oder ein qrel ohne passende Frage/Absatz."""


def _spalten(pfad: Path, namen: tuple[str, ...]) -> list[dict]:
    """Eine Arrow-IPC-Stream-Datei als Liste von Zeilen-Dicts. Lazy-Import von pyarrow."""
    try:
        import pyarrow as pa
    except ImportError as exc:
        raise GermanQuadFehler(
            "pyarrow fehlt für den GermanQuAD-Korpus — `uv sync --extra eval` ausführen."
        ) from exc
    if not pfad.exists():
        raise GermanQuadFehler(f"GermanQuAD-Datei nicht gefunden: {pfad}")
    tabelle = pa.ipc.open_stream(pa.memory_map(str(pfad))).read_all()
    fehlend = [n for n in namen if n not in tabelle.schema.names]
    if fehlend:
        raise GermanQuadFehler(f"{pfad}: Spalten {fehlend} fehlen (vorhanden: {tabelle.schema.names})")
    return tabelle.select(list(namen)).to_pylist()


def _fundstellen(zeilen: list[dict]) -> tuple[Fundstelle, ...]:
    """Je Korpuszeile eine Fundstelle; die Korpus-ID ist zugleich `id`, `datei_name` und
    `datei_hash` — dieser Korpus kennt keine Dateien, nur Absätze."""
    return tuple(
        Fundstelle(
            id=z["_id"], datei_hash=z["_id"], datei_name=z["_id"], seite=1, absatz=1, text=z["text"]
        )
        for z in zeilen
    )


def _fragen(qrels: list[dict], frage_je_id: dict[str, str], absatz_ids: frozenset[str]) -> tuple[dict, ...]:
    """Golden-Form wie `beispiele/malerbetrieb/golden.json`, plus `absatz_id` für den
    absatzgenauen Treffer. `datei` == `absatz_id`, weil eine Korpuszeile beides ist."""
    fragen: list[dict] = []
    for q in qrels:
        frage_id, absatz_id = q["query-id"], q["corpus-id"]
        if frage_id not in frage_je_id:
            raise GermanQuadFehler(f"qrels verweist auf unbekannte Frage: {frage_id}")
        if absatz_id not in absatz_ids:
            raise GermanQuadFehler(f"qrels verweist auf unbekannten Absatz: {absatz_id}")
        fragen.append(
            {
                "frage": frage_je_id[frage_id],
                "status": "gefunden",
                "datei": absatz_id,
                "absatz_id": absatz_id,
            }
        )
    return tuple(fragen)


def ziehe_fragen(fragen: tuple[dict, ...], anzahl: int | None, seed: int) -> tuple[dict, ...]:
    """Deterministische Stichprobe in Ausgangsreihenfolge. `None` oder `anzahl >= len` gibt
    alles unverändert zurück — eine Ziehung, die nichts weglässt, soll auch nichts umsortieren."""
    if anzahl is None or anzahl >= len(fragen):
        return fragen
    plaetze = sorted(random.Random(seed).sample(range(len(fragen)), anzahl))
    return tuple(fragen[i] for i in plaetze)


def lade(
    ordner: Path = STANDARD_ORDNER, *, fragen: int | None = None, seed: int = 42
) -> tuple[tuple[Fundstelle, ...], tuple[dict, ...]]:
    """`(fundstellen, fragen)` in genau den Typen, die `retrieval_eval` schon benutzt:
    `Fundstelle` je Korpus-Absatz, golden-Dicts je Frage. `fragen=N` zieht deterministisch
    eine Stichprobe (Default: alle)."""
    ordner = Path(ordner)
    korpus = _spalten(ordner / "corpus.arrow", ("_id", "text"))
    anfragen = _spalten(ordner / "queries.arrow", ("_id", "text"))
    qrels = _spalten(ordner / "qrels.arrow", ("query-id", "corpus-id"))
    fundstellen = _fundstellen(korpus)
    alle = _fragen(qrels, {z["_id"]: z["text"] for z in anfragen}, frozenset(f.id for f in fundstellen))
    return fundstellen, ziehe_fragen(alle, fragen, seed)
