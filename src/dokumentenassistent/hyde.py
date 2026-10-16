"""HyDE: nicht die Frage einbetten, sondern eine hypothetische Antwort darauf.

Anlass, gemessen 25.09.2026 am echten Bestand: die Wortüberlappung zwischen Frage und
Zielabsatz liegt im Median bei **0,11** — gegen 0,60 bei menschlichen GermanQuAD-Fragen.
Acht von 85 Fragen teilen mit ihrem Zielabsatz *kein einziges* inhaltliches Wort. Die
rohe Frage einzubetten ist damit der schwerste denkbare Suchmodus, und die Messung zeigt
die Folge: 29 von 85 Stellen erreichen den Prompt nie, 16 davon erscheinen nicht einmal
unter den ersten fünfzig.

Die Idee ist alt und einfach: Ein Sprachmodell schreibt, wie die Antwort *aussähe* —
„Der Rechnungsbetrag beträgt … EUR, zahlbar bis …" — und dieser Text wird eingebettet.
Er ist dem Zielabsatz sprachlich viel näher als die Frage, gerade weil er dessen
Formulierungen imitiert statt sie zu umschreiben.

Der Text darf frei erfunden sein. Gesucht wird mit seinem *Vektor*, nicht mit seinem
Inhalt; belegt wird weiterhin ausschließlich aus echten Absätzen. Eine erfundene Zahl
darin kann keine falsche Antwort erzeugen — sie kann nur die Suche in die richtige
Nachbarschaft lenken oder eben nicht.

**Hängt an keinem Produktpfad.** `suche()` ruft das hier nicht auf. Erst messen.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dokumentenassistent.provider import ModelProvider

ANWEISUNG = (
    "Schreibe zwei bis drei Sätze, wie die Antwort auf diese Frage in einem "
    "deutschen Geschäftsdokument formuliert wäre — im Stil des Dokuments, nicht "
    "im Stil einer Antwort. Erfinde konkrete Werte (Beträge, Daten, Nummern, Namen), "
    "wenn welche hingehören. Keine Einleitung, keine Erklärung, nur der Text.\n\n"
    "Frage: {frage}\n"
    "Dokumenttext:"
)


def hypothese(frage: str, provider: ModelProvider) -> str:
    """Ein erfundener Dokumentabsatz zur Frage. Leere Antwort -> die Frage selbst.

    Der Rückfall auf die Frage ist wichtig: ein Modell, das hier nichts liefert, darf
    die Suche nicht auf einen leeren Vektor schicken. Dann sucht man eben wie bisher.
    """
    text = provider.generate_text(ANWEISUNG.format(frage=frage)).strip()
    return text or frage


def suchtext(frage: str, provider: ModelProvider, mit_frage: bool = True) -> str:
    """Was eingebettet wird. `mit_frage=True` hängt die Frage an die Hypothese.

    Warum beides: Die Hypothese trifft den Stil des Zielabsatzes, die Frage hält die
    Begriffe fest, die wirklich vorkommen (Eigennamen, Nummern). Welche Variante hier
    gewinnt, ist offen — deshalb ist es ein Schalter und keine Entscheidung.
    """
    h = hypothese(frage, provider)
    return f"{h}\n\n{frage}" if mit_frage else h
