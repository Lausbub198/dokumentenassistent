"""Erst auswählen, dann antworten — in ZWEI Modellaufrufen.

Gemessen 25.09.2026 am echten Bestand: von 56 Fragen, deren Antwort nachweislich im
Prompt steht, beantwortet gemma4:12b nur 39 richtig. 11-mal sagt es „nicht gefunden",
7-mal zitiert es aus der falschen Datei — obwohl die richtige Stelle vor ihm liegt.

Der Verdacht ist nicht „das Modell ist zu schwach", sondern „die Aufgabe ist zu groß":
Bei `top_n=20` stehen 30.069 Zeichen im Prompt (Median), und das Modell soll darin
gleichzeitig die richtige Stelle FINDEN und daraus eine belegte Antwort FORMULIEREN.

Hier sind das zwei Aufrufe:

    1. Auswahl:  20 Absätze, nur IDs zurück. Eine Klassifikation, keine Formulierung.
    2. Antwort:  1-3 Absätze, dieselbe Anweisung wie bisher. Kurzer Prompt.

**Nicht zu verwechseln mit der gemessenen Fehlvariante `zwei_schritte`** aus
`anweisungen.py`: die packte beide Schritte in EINEN Prompt und war schlechter als die
Ausgangsfassung (37 statt 38 richtig, 13 statt 7 falsche Dateien). Ein Modell, das in
einem Zug auswählen und formulieren soll, tut beides halb. Getrennte Aufrufe sind eine
andere Sache — der zweite sieht nur noch, was der erste ausgewählt hat.

**Hängt an keinem Produktpfad.** Erst messen.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dokumentenassistent.typen import Fundstelle

if TYPE_CHECKING:
    from dokumentenassistent.provider import ModelProvider

_ID = re.compile(r"\[?([^\[\]\s]+#S\d+#A\d+)\]?")

AUSWAHL = (
    "Welche der folgenden Absätze enthalten die Antwort auf die Frage?\n"
    "Antworte NUR mit den Absatz-IDs in eckigen Klammern, höchstens drei, "
    "der wichtigste zuerst. Keine Erklärung, keine Antwort auf die Frage.\n"
    "Enthält kein Absatz die Antwort, schreibe genau \"keiner\".\n\n"
    "Absätze:\n{absaetze}\n\nFrage: {frage}\nIDs:"
)


def waehle(frage: str, absaetze: tuple[Fundstelle, ...], provider: ModelProvider,
           hoechstens: int = 3) -> tuple[Fundstelle, ...]:
    """Schritt 1. Gibt die genannten Absätze in der genannten Reihenfolge zurück.

    IDs, die nicht in `absaetze` vorkommen, werden verworfen — ein Modell, das eine
    ID erfindet, darf keinen Absatz aus dem Nichts in den zweiten Schritt schleusen.
    Nennt es nichts Gültiges, bleibt es bei `()`, und der Aufrufer entscheidet.
    """
    if not absaetze:
        return ()
    nach_id = {f.id: f for f in absaetze}
    text = provider.generate_text(AUSWAHL.format(
        absaetze="\n\n".join(f"[{f.id}]\n{f.text}" for f in absaetze), frage=frage))
    gewaehlt: list[Fundstelle] = []
    for id_ in _ID.findall(text):
        f = nach_id.get(id_)
        if f is not None and f not in gewaehlt:
            gewaehlt.append(f)
        if len(gewaehlt) >= hoechstens:
            break
    return tuple(gewaehlt)
