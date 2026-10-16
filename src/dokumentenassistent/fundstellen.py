"""M4: Seiten in zitierbare Fundstellen (Absätze bzw. Fenster) zerlegen.

Ein Absatz ist ein durch eine Leerzeile getrennter Textblock. Fehlen
Leerzeilen auf einer Seite, gilt die ganze Seite als ein Absatz. Absätze
über `max_woerter` werden in überlappende Fenster geteilt; jedes Fenster
bekommt eine eigene, fortlaufende Absatznummer.
"""
from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass

from dokumentenassistent.typen import Datei, Fundstelle, Seite, SeitenSpanne

_LEERZEILE = re.compile(r"\n\s*\n")
_MEHRFACH_LEERZEICHEN = re.compile(r" {2,}")


def fundstellen_id(datei_hash: str, seite: int, absatz: int, text: str) -> str:
    """Content-addressed, independent of path or display name."""
    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:20]
    return f"D{datei_hash}#S{seite}#A{absatz}#T{text_hash}"


def eindeutige_ids(fundstellen: tuple[Fundstelle, ...]) -> dict[str, Fundstelle]:
    """Current IDs plus unique legacy display aliases in this exact context."""
    by_id = {f.id: f for f in fundstellen}
    aliases: dict[str, list[Fundstelle]] = {}
    for f in fundstellen:
        alias = f'{f.datei_name}#S{f.seite}#A{f.absatz}'
        aliases.setdefault(alias, []).append(f)
    for alias, matches in aliases.items():
        if len(matches) == 1 and alias not in by_id:
            by_id[alias] = matches[0]
    return by_id


def _normalisiere_absatz(roh: str) -> str:
    """Zeilen einzeln trimmen, Mehrfach-Leerzeichen zu einem, leere Zeilen weg."""
    zeilen = [_MEHRFACH_LEERZEICHEN.sub(" ", zeile.strip()) for zeile in roh.split("\n")]
    return "\n".join(z for z in zeilen if z)


def _fenster(woerter: list[str], max_woerter: int, ueberlapp: int) -> list[list[str]]:
    """Wortliste in überlappende Fenster teilen (nur aufgerufen, wenn zu lang)."""
    schritt = max_woerter - ueberlapp
    ergebnis: list[list[str]] = []
    start = 0
    while start < len(woerter):
        ende = start + max_woerter
        ergebnis.append(woerter[start:ende])
        if ende >= len(woerter):
            break
        start += schritt
    return ergebnis


def _verschmelze(teile: list[str], min_woerter: int, max_woerter: int) -> list[str]:
    """Aufeinanderfolgende Stücke zusammenlegen, bis `min_woerter` erreicht ist.

    Gemessen 24.09.2026 am echten Bestand (2458 Absätze, 54 Fragen): ohne Untergrenze
    sind 1103 Absätze kürzer als 10 Wörter — Kopfzeilen, Seitenzahlen, Tabellenzellen,
    Adressfragmente. Die Zielabsätze der Fragen haben 94 Wörter im Median. Die Suche
    musste also durch ein Feld aus Rauschen, in dem ein 6-Wort-Fragment einen schärferen
    Vektor hat als ein 94-Wort-Absatz. Verschmelzen bis 120 Wörter: 2458 → 788 Stücke,
    MRR 0,495 → 0,596, R@1 41 → 52 %, R@20 72 → 80 %.

    Gegen `semantic-text-splitter` gemessen (Spannen 500–1500 und 800–2400 Zeichen, mit
    und ohne Überlappung): die Bibliothek bleibt darunter (bestes MRR 0,558), weil sie
    nach Zeichen schneidet und mitten durch einen Absatz darf. Bei Geschäftspost trägt
    ein Absatz oft genau eine Aussage — deshalb wird hier nur zusammengelegt, nie geteilt.
    """
    if min_woerter <= 0:
        return teile
    raus: list[str] = []
    puffer: list[str] = []
    laenge = 0
    for teil in teile:
        n = len(teil.split())
        if puffer and laenge + n > max_woerter:
            raus.append("\n".join(puffer))
            puffer, laenge = [], 0
        puffer.append(teil)
        laenge += n
        if laenge >= min_woerter:
            raus.append("\n".join(puffer))
            puffer, laenge = [], 0
    if puffer:
        raus.append("\n".join(puffer))
    return raus


@dataclass(frozen=True)
class _Stueck:
    text: str
    seiten: tuple[int | None, ...]  # eine Herkunft je Zeichen; None = eingefügter Trenner


def _verbinde(teile: list[_Stueck], trenner: str) -> _Stueck:
    return _Stueck(trenner.join(t.text for t in teile),
                   tuple(wert for i, teil in enumerate(teile)
                         for wert in ((None,) * len(trenner) if i else ()) + teil.seiten))


def _normalisiere_mit_seiten(text: str, seiten: tuple[int | None, ...]) -> _Stueck:
    zeilen: list[_Stueck] = []
    position = 0
    for rohzeile in text.split('\n'):
        herkunft = seiten[position:position + len(rohzeile)]
        position += len(rohzeile) + 1
        links = len(rohzeile) - len(rohzeile.lstrip())
        rechts = len(rohzeile.rstrip())
        zeile = rohzeile[links:rechts]
        herkunft = herkunft[links:rechts]
        if not zeile:
            continue
        zeichen: list[str] = []
        ursprung: list[int | None] = []
        i = 0
        while i < len(zeile):
            if zeile[i] == ' ':
                ende = i + 1
                while ende < len(zeile) and zeile[ende] == ' ':
                    ende += 1
                zeichen.append(' ')
                ursprung.append(herkunft[i])
                i = ende
            else:
                zeichen.append(zeile[i])
                ursprung.append(herkunft[i])
                i += 1
        zeilen.append(_Stueck(''.join(zeichen), tuple(ursprung)))
    return _verbinde(zeilen, '\n') if zeilen else _Stueck('', ())


def _spannen(stueck: _Stueck) -> tuple[SeitenSpanne, ...]:
    ergebnis: list[SeitenSpanne] = []
    aktuelle_seite: int | None = None
    start = 0
    ende = 0
    for position, seite in enumerate(stueck.seiten):
        if seite is None:
            if aktuelle_seite is not None:
                ergebnis.append(SeitenSpanne(aktuelle_seite, start, ende))
                aktuelle_seite = None
            continue
        if seite != aktuelle_seite:
            if aktuelle_seite is not None:
                ergebnis.append(SeitenSpanne(aktuelle_seite, start, ende))
            aktuelle_seite, start = seite, position
        ende = position + 1
    if aktuelle_seite is not None:
        ergebnis.append(SeitenSpanne(aktuelle_seite, start, ende))
    return tuple(ergebnis)


def _verschmelze_stuecke(teile: list[_Stueck], min_woerter: int,
                         max_woerter: int) -> list[_Stueck]:
    if min_woerter <= 0:
        return teile
    raus: list[_Stueck] = []
    puffer: list[_Stueck] = []
    laenge = 0
    for teil in teile:
        n = len(teil.text.split())
        if puffer and laenge + n > max_woerter:
            raus.append(_verbinde(puffer, '\n'))
            puffer, laenge = [], 0
        puffer.append(teil)
        laenge += n
        if laenge >= min_woerter:
            raus.append(_verbinde(puffer, '\n'))
            puffer, laenge = [], 0
    if puffer:
        rest = _verbinde(puffer, '\n')
        if (raus and laenge < min(min_woerter, 5)
                and len(raus[-1].text.split()) + laenge <= max_woerter):
            raus[-1] = _verbinde([raus[-1], rest], '\n')
        else:
            raus.append(rest)
    return raus


def _zerlege_dokumentweit(datei: Datei, seiten: tuple[Seite, ...],
                          max_woerter: int, ueberlapp: int,
                          min_woerter: int) -> tuple[Fundstelle, ...]:
    inhalte = [_Stueck(seite.text, (seite.nummer,) * len(seite.text))
               for seite in seiten if seite.text.strip()]
    if not inhalte:
        return ()
    dokument = inhalte[0]
    for teil in inhalte[1:]:
        # Eine vorhandene Rand-Zeilenumbruchfolge nicht abschneiden oder durch
        # einen zusätzlichen Umbruch zu einem künstlichen Absatzbruch machen.
        trenner = '' if dokument.text.endswith('\n') or teil.text.startswith('\n') else '\n'
        dokument = _verbinde([dokument, teil], trenner)
    teile: list[_Stueck] = []
    start = 0
    for treffer in list(_LEERZEILE.finditer(dokument.text)) + [None]:
        ende = treffer.start() if treffer else len(dokument.text)
        teil = _normalisiere_mit_seiten(dokument.text[start:ende], dokument.seiten[start:ende])
        start = treffer.end() if treffer else ende
        if not teil.text:
            continue
        woerter = list(re.finditer(r'\S+', teil.text))
        if len(woerter) <= max_woerter:
            teile.append(teil)
        else:
            wort_stuecke = [_Stueck(m.group(), teil.seiten[m.start():m.end()]) for m in woerter]
            teile.extend(_verbinde(fenster, ' ') for fenster in
                         _fenster(wort_stuecke, max_woerter, ueberlapp))
    zaehler: dict[int, int] = {}
    fundstellen: list[Fundstelle] = []
    for teil in _verschmelze_stuecke(teile, min_woerter, max_woerter):
        spannen = _spannen(teil)
        seite = spannen[0].seite
        zaehler[seite] = zaehler.get(seite, 0) + 1
        absatz = zaehler[seite]
        fundstellen.append(Fundstelle(
            id=fundstellen_id(datei.hash, seite, absatz, teil.text),
            datei_hash=datei.hash, datei_name=datei.name, seite=seite,
            absatz=absatz, text=teil.text, spannen=spannen))
    return tuple(fundstellen)


def zerlege(
    datei: Datei,
    seiten: tuple[Seite, ...],
    max_woerter: int = 380,
    ueberlapp: int = 30,
    min_woerter: int = 120,
    seitenuebergreifend: bool = False,
) -> tuple[Fundstelle, ...]:
    if seitenuebergreifend:
        return _zerlege_dokumentweit(datei, seiten, max_woerter, ueberlapp, min_woerter)
    fundstellen: list[Fundstelle] = []
    for seite in seiten:
        roh_teile: list[str] = []
        for roh in _LEERZEILE.split(seite.text):
            text = _normalisiere_absatz(roh)
            if not text:
                continue
            woerter = text.split()
            if len(woerter) <= max_woerter:
                roh_teile.append(text)
            else:
                roh_teile.extend(" ".join(w) for w in _fenster(woerter, max_woerter, ueberlapp))
        # Verschmolzen wird nur innerhalb einer Seite: ein Beleg muss auf genau eine
        # Seite zeigen, sonst stimmt die Fundstelle nicht mehr.
        for absatznummer, teil in enumerate(
            _verschmelze(roh_teile, min_woerter, max_woerter), start=1
        ):
            fundstellen.append(
                Fundstelle(
                    id=fundstellen_id(datei.hash, seite.nummer, absatznummer, teil),
                    datei_hash=datei.hash,
                    datei_name=datei.name,
                    seite=seite.nummer,
                    absatz=absatznummer,
                    text=teil,
                )
            )
    return tuple(fundstellen)
