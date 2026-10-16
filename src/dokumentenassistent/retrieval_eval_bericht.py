"""Bericht aus `laeufe.jsonl`: Tabelle Variante × Embedding, darunter „Wo es bricht"
(je Frage, welchen Rang sie in welcher Variante findet). Der Bericht rechnet nichts nach.

Seit 22.09.2026 zusätzlich eine zweite Tabelle „Absatzgenau", sobald Zeilen das Feld
`absatzgenau` tragen (GermanQuAD: die Frage nennt den Zielabsatz, nicht nur die Datei).
Sie fehlt bei malerbetrieb-Läufen — dort gibt es diesen Maßstab nicht, und eine leere
Spalte wäre eine Behauptung.
"""
from __future__ import annotations

import json
from pathlib import Path

# @3/@12/@20 seit 23.09.2026: `top_n` (8) und `rerank_k` (20) waren nie gemessen —
# die Spalten zeigen, was ein engeres bzw. weiteres Prompt-Fenster einfängt.
RECALL_K = (1, 3, 5, 8, 12, 20)

SPALTEN = (
    "Variante", "Embedding", "Fundstellen", "Embed s", *(f"Recall@{k}" for k in RECALL_K),
    "MRR", "Nicht-gefunden-Quote %", "Dauer/Frage s",
)


def lese_laeufe(pfad: Path) -> tuple[dict, ...]:
    if not pfad.exists():
        return ()
    return tuple(json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip())


def _letzte_je_lauf(zeilen: tuple[dict, ...]) -> dict[tuple[str, str | None], dict]:
    """Bei Wiederholung derselben (Variante, Embedding) zählt die letzte Zeile."""
    return {(z["variante"], z.get("embedding")): z for z in zeilen}


def _prozent(wert: float | None) -> str:
    return "–" if wert is None else f"{wert * 100:.0f}"


def _zeile(z: dict) -> str:
    werte = (
        z["variante"], z.get("embedding") or "–", z["fundstellenzahl"],
        f"{z['embed_sekunden']:.1f}" if z.get("embed_sekunden") is not None else "–",
        *(_prozent(z.get(f"recall_at_{k}")) for k in RECALL_K),
        z.get("mrr") if z.get("mrr") is not None else "–",
        _prozent(z.get("nicht_gefunden_treffer_quote")), f"{z.get('dauer_s_frage_avg', 0.0):.3f}",
    )
    return "| " + " | ".join(str(w) for w in werte) + " |"


def _tabelle(laeufe: dict[tuple[str, str | None], dict]) -> str:
    kopf = "| " + " | ".join(SPALTEN) + " |\n|" + "---|" * len(SPALTEN)
    zeilen = sorted(laeufe.values(), key=lambda z: (z["variante"], z.get("embedding") or ""))
    return f"{kopf}\n" + "\n".join(_zeile(z) for z in zeilen)


ABSATZ_SPALTEN = ("Variante", "Embedding", *(f"Recall@{k}" for k in RECALL_K), "MRR")


def _absatz_tabelle(laeufe: dict[tuple[str, str | None], dict]) -> str:
    """Zweiter Maßstab: nicht „ein Absatz der richtigen Datei", sondern genau der Zielabsatz."""
    mit_absatz = [z for z in laeufe.values() if z.get("absatzgenau")]
    if not mit_absatz:
        return ""
    kopf = "| " + " | ".join(ABSATZ_SPALTEN) + " |\n|" + "---|" * len(ABSATZ_SPALTEN)
    zeilen = []
    for z in sorted(mit_absatz, key=lambda z: (z["variante"], z.get("embedding") or "")):
        a = z["absatzgenau"]
        werte = (
            z["variante"], z.get("embedding") or "–",
            *(_prozent(a.get(f"recall_at_{k}")) for k in RECALL_K),
            a.get("mrr") if a.get("mrr") is not None else "–",
        )
        zeilen.append("| " + " | ".join(str(w) for w in werte) + " |")
    return (
        "## Absatzgenau\n\nTreffer = genau der Zielabsatz (`absatz_id`), nicht nur die richtige Datei.\n\n"
        + kopf + "\n" + "\n".join(zeilen) + "\n\n"
    )


def _wo_es_bricht(laeufe: dict[tuple[str, str | None], dict]) -> str:
    schluessel = sorted(laeufe, key=lambda s: (s[0], s[1] or ""))
    fragen: list[str] = []
    for z in laeufe.values():
        fragen.extend(f["frage"] for f in z.get("fragen") or [] if f["frage"] not in fragen)
    kopf = (
        "| Frage | " + " | ".join(f"{v}@{e or '-'}" for v, e in schluessel) + " |\n|---|" + "---|" * len(schluessel)
    )
    zeilen = []
    for frage in fragen:
        zellen = []
        for s in schluessel:
            raenge = {f["frage"]: f["rang"] for f in laeufe[s].get("fragen") or []}
            if frage not in raenge:
                zellen.append("–")
            else:
                zellen.append(str(raenge[frage]) if raenge[frage] is not None else "nicht gefunden")
        zeilen.append(f"| {frage} | " + " | ".join(zellen) + " |")
    return "## Wo es bricht\n\n" + kopf + "\n" + "\n".join(zeilen)


def baue_bericht(zeilen: tuple[dict, ...]) -> str:
    laeufe = _letzte_je_lauf(zeilen)
    if not laeufe:
        return "# Retrieval-Eval\n\nKeine Läufe.\n"
    erster = next(iter(laeufe.values()))
    kopf = f"# Retrieval-Eval — {erster.get('korpus', '')}, Stufe {erster.get('stufe', '')}\n\n"
    return kopf + _tabelle(laeufe) + "\n\n" + _absatz_tabelle(laeufe) + _wo_es_bricht(laeufe) + "\n"


def schreibe_bericht(ordner: Path) -> Path:
    zeilen = lese_laeufe(Path(ordner) / "laeufe.jsonl")
    ziel = Path(ordner) / "bericht.md"
    ziel.write_text(baue_bericht(zeilen), encoding="utf-8")
    return ziel
