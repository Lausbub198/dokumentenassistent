"""M7 — Fundstellen + Profil → Vorschlag.

Fragt das Modell nach Kategorie, Typ und Feldern, lässt jeden behaupteten Beleg
deterministisch prüfen (M8) und baut daraus den Zielnamen. Das Modell darf nur
Fundstellen-IDs aus der übergebenen Liste zitieren; alles Unbelegte wird unklar.
"""
from __future__ import annotations

import copy
import dataclasses
import re
from typing import TYPE_CHECKING, Mapping

from dokumentenassistent.typen import Beleg, Datei, Feld, Fundstelle, Profil, Status, Vorschlag
from dokumentenassistent.zitatpruefung import pruefe_felder
from dokumentenassistent.fundstellen import eindeutige_ids

if TYPE_CHECKING:
    from dokumentenassistent.provider import ModelProvider


EINORDNUNG_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "kategorie": {"type": "string"},
        "typ": {"type": "string"},
        "felder": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "wert": {"type": "string"},
                    "fundstelle_id": {"type": "string"},
                    "wortlaut": {"type": "string"},
                },
                "required": ["name", "wert", "fundstelle_id", "wortlaut"],
            },
        },
        "begruendung": {"type": "string"},
    },
    "required": ["kategorie", "typ", "felder", "begruendung"],
}

_VERBOTENE_ZEICHEN = '/\\:*?"<>|'
_UNBEKANNT = "unbekannt"


def _schema(fundstellen: tuple[Fundstelle, ...], profil: Profil) -> dict:
    """Schema je Aufruf: Fundstellen-IDs, Feldnamen, Kategorie und Typ als enum.

    Ohne enum kopierte das Modell die ID mitsamt eckigen Klammern aus dem Prompt
    ("[Rechnung (2).pdf#S1#A1]") — jede Zitatprüfung scheiterte am Lookup.
    Mit enum kann es nur eine ID zitieren, die es wirklich gibt.
    """
    schema = copy.deepcopy(EINORDNUNG_SCHEMA)
    eintrag = schema["properties"]["felder"]["items"]["properties"]
    eintrag["fundstelle_id"]["enum"] = [f.id for f in fundstellen]
    eintrag["name"]["enum"] = list(profil.felder)
    schema["properties"]["kategorie"]["enum"] = [*profil.kategorien, _UNBEKANNT]
    schema["properties"]["typ"]["enum"] = [*profil.dokumenttypen, _UNBEKANNT]
    return schema


def _eigentuemer_hinweis(profil: Profil) -> str:
    """Ohne „wer bin ich" kann kein Modell eine Eingangs- von einer Ausgangsrechnung unterscheiden."""
    if not profil.eigentuemer:
        return ""
    return (
        f"Eigentümer des Bestands: {profil.eigentuemer}. Dokumente, die der Eigentümer selbst "
        "ausgestellt hat (Rechnungen, Angebote, Schreiben an andere), sind AUSGEHEND; Dokumente "
        "anderer an den Eigentümer sind EINGEHEND. Gibt es Kategorien für beide Richtungen, "
        "entscheidet der Aussteller.\n"
    )


def _baue_prompt(datei: Datei, fundstellen: tuple[Fundstelle, ...], profil: Profil) -> str:
    absaetze = "\n".join(f"[{f.id}] {f.text}" for f in fundstellen)
    return (
        f"Zweck des Dokumentenbestands: {profil.zweck}\n"
        f"{_eigentuemer_hinweis(profil)}"
        f"Dokument: {datei.name}\n\n"
        f"Erlaubte Kategorien (nur diese, sonst wörtlich \"{_UNBEKANNT}\"): "
        f"{', '.join(profil.kategorien)}\n"
        f"Erlaubte Dokumenttypen (nur diese, sonst wörtlich \"{_UNBEKANNT}\"): "
        f"{', '.join(profil.dokumenttypen)}\n"
        f"Zu erfassende Felder: {', '.join(profil.felder)}\n\n"
        f"Absätze des Dokuments, jeweils [ID] Text:\n{absaetze}\n\n"
        "Ordne das Dokument ein: Kategorie und Dokumenttyp aus den erlaubten Listen. "
        "Nennt das Dokument eines der Objekte aus der Kategorienliste (auch als Leistungsort, "
        "Mietobjekt, Grundstück oder Objekt), dann ist GENAU diese Kategorie richtig — "
        "prüfe die Liste Wort für Wort, bevor du sie verwirfst. Nennt es kein solches Objekt, "
        "nimm die Sammelkategorie (z. B. \"Sonstiges\"), falls es eine gibt. "
        "\"unbekannt\" nur, wenn das Dokument nichts mit dem Zweck des Bestands zu tun hat. "
        "Gib zu jedem Feld den Wert, die Fundstellen-ID des Absatzes und den WÖRTLICHEN "
        "Ausschnitt aus genau diesem Absatz an, der den Wert belegt. "
        "Die Fundstellen-ID genau so wie in der Liste, ohne die eckigen Klammern. "
        "Erfinde nichts: zitiere nur Fundstellen-IDs aus der Liste oben und nur Text, "
        "der wörtlich in diesem Absatz steht. Ein Feld, dessen Wert nicht im Dokument "
        "steht, wird nicht aufgeführt; ein Platzhalter ist kein Wert. Der Wert selbst muss "
        "im zitierten Ausschnitt stehen. "
        "Datumswerte im Format YYYY-MM-DD. Beträge so, wie sie im Dokument "
        "stehen, mit Tausenderpunkt, Dezimalkomma und Währung (z. B. 1.240,00 EUR); "
        "als Betrag gilt der Hauptbetrag des Dokuments (Rechnungs-, Gesamt- oder "
        "Jahresbetrag), nicht ein Einzelposten. Der Aussteller ist die Firma oder Stelle, "
        "die das Dokument herausgegeben hat, mit vollem Namen wie im Dokument. "
        "Antworte auf Deutsch."
    )


def _aus_profil(wert: object, erlaubt: tuple[str, ...]) -> str | None:
    return wert if isinstance(wert, str) and wert in erlaubt else None


_LEERE_WERTE = frozenset({"", "unbekannt", "-", "k.a.", "keine", "null", "none", "n/a"})


def _nichts_behauptet(eintrag: Mapping[str, object]) -> bool:
    """Kein Wortlaut und der Wert ist leer oder ein Platzhalter.

    Die Fundstellen-ID zählt nicht: Das Schema erzwingt sie als Pflichtfeld mit enum,
    das Modell füllt sie deshalb auch dann, wenn es nichts zu belegen hat.
    """
    wert = str(eintrag.get("wert") or "").strip().lower()
    kein_wortlaut = not str(eintrag.get("wortlaut") or "").strip()
    return kein_wortlaut and wert in _LEERE_WERTE


def _felder_aus_antwort(
    antwort: Mapping[str, object], profil: Profil, fundstellen: Mapping[str, Fundstelle]
) -> tuple[Feld, ...]:
    """Modell-Felder zu Feld+Beleg, geprüft; nicht gelieferte Profilfelder als 'fehlt' ergänzt."""
    behauptet: dict[str, Feld] = {}
    erlaubte = eindeutige_ids(tuple(fundstellen.values()))
    eintraege = antwort.get("felder") or []
    for eintrag in eintraege if isinstance(eintraege, list) else []:
        name = eintrag.get("name")
        if name not in profil.felder or name in behauptet:
            continue
        if _nichts_behauptet(eintrag):
            continue  # Modell hat das Feld nur formal mitgeliefert → 'fehlt', kein gebrochener Beleg
        behauptet[name] = Feld(
            name=name,
            wert=eintrag.get("wert"),
            beleg=Beleg(
                fundstelle_id=(erlaubte[eintrag.get('fundstelle_id')].id
                                if eintrag.get('fundstelle_id') in erlaubte else ""),
                wortlaut=eintrag.get("wortlaut") or "",
            ),
            status="belegt",
        )
    geprueft = pruefe_felder(tuple(behauptet[n] for n in profil.felder if n in behauptet), fundstellen)
    # Nach der Belegprüfung (der Wert muss im Dokument so stehen, wie es ihn schreibt), dann einheitlich.
    geprueft = tuple(_mit_iso_datum(f) for f in geprueft)
    nach_name = {f.name: f for f in geprueft}
    return tuple(nach_name.get(n, Feld(name=n, wert=None, beleg=None, status="fehlt")) for n in profil.felder)


def baue_zielname(
    profil: Profil, kategorie: str, typ: str, felder: tuple[Feld, ...], endung: str, original: str = ""
) -> str | None:
    """Namensschema füllen.

    Ein Platzhalter, dessen Feld das Modell nicht geliefert hat ('fehlt'), wird durch den
    Original-Dateinamen ersetzt — eine Besprechungsnotiz hat keinen Aussteller und soll
    trotzdem einen Zielnamen bekommen. Ein Platzhalter mit gebrochenem Beleg ('unklar')
    ergibt None: da stimmt etwas nicht, das entscheidet der Mensch.
    """
    werte: dict[str, str | None] = {"typ": typ, "kategorie": kategorie}
    fehlt: set[str] = set()
    for feld in felder:
        werte[feld.name] = feld.wert if feld.status == "belegt" else None
        if feld.status == "fehlt":
            fehlt.add(feld.name)

    name = profil.namensschema
    for platzhalter in re.findall(r"\{(\w+)\}", profil.namensschema):
        wert = werte.get(platzhalter)
        if not wert and platzhalter in fehlt and original:
            wert = original
        if not wert:
            return None
        name = name.replace("{" + platzhalter + "}", wert)

    for zeichen in _VERBOTENE_ZEICHEN:
        name = name.replace(zeichen, "-")
    return re.sub(r" +", " ", name).strip() + endung


def _status(
    kategorie: str | None,
    typ: str | None,
    felder: tuple[Feld, ...],
    zielname: str | None,
    ocr_unsicher: bool,
) -> Status:
    """sicher = Kategorie und Typ im Profil, Zielname baubar, kein Feld mit gebrochenem Beleg.

    Ein Feld, das das Modell gar nicht geliefert hat ('fehlt'), verhindert 'sicher' nicht:
    ein Mietvertrag ohne Rechnungsnummer ist kein unsicheres Dokument. Nur ein behaupteter,
    aber nicht haltbarer Beleg ('unklar') macht die ganze Zeile unklar.
    """
    if ocr_unsicher:
        return "ocr_unsicher"
    if any(_wert_unplausibel(f) for f in felder):
        return "unklar"
    if kategorie and typ and zielname and not any(f.status == "unklar" for f in felder):
        return "sicher"
    return "unklar"


# Füllsätze, die Modelle statt eines Werts liefern. Gefunden 10.10.2026: Untitled.pdf bekam den
# Zielnamen „nicht im Dokument enthalten_Bescheinigung_Untitled.pdf“ und stand trotzdem auf „sicher“.
_FUELLSAETZE = ("nicht im dokument", "nicht enthalten", "nicht angegeben", "keine angabe", "unbekannt", "n/a")
_DATUM = re.compile(r"\d{4}-\d{2}-\d{2}")


_MONATE = {m: i for i, m in enumerate(("januar februar märz april mai juni juli august september "
                                       "oktober november dezember").split(), start=1)}
_PUNKT_DATUM = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
_MONATS_DATUM = re.compile(r"(\d{1,2})\.\s*([a-zä]+)\s+(\d{4})")


def normalisiere_datum(wert: str) -> str:
    """Vollständige Daten in anderem Format (12.03.2025, 3. März 2025) auf YYYY-MM-DD bringen.
    Unvollständiges („30.04.“, „2025-03“) bleibt unverändert — das fängt `_wert_unplausibel`.
    Anlass 10.10.2026 (Lab-Nachmessung): 7 von 11 Datumsfällen waren korrekte Daten in anderem Format."""
    text = wert.strip()
    if _DATUM.fullmatch(text):
        return text
    if m := _PUNKT_DATUM.fullmatch(text):
        tag, monat, jahr = int(m[1]), int(m[2]), m[3]
    elif (m := _MONATS_DATUM.fullmatch(text.lower())) and m[2] in _MONATE:
        tag, monat, jahr = int(m[1]), _MONATE[m[2]], m[3]
    else:
        return wert
    return f"{jahr}-{monat:02d}-{tag:02d}" if 1 <= monat <= 12 and 1 <= tag <= 31 else wert


def _mit_iso_datum(feld: Feld) -> Feld:
    if feld.name != "datum" or feld.status != "belegt" or not feld.wert:
        return feld
    return dataclasses.replace(feld, wert=normalisiere_datum(feld.wert))


def _wert_unplausibel(feld: Feld) -> bool:
    """Feste Regel ohne Modell: ein belegter Wert, der kein Wert ist, macht die Zeile unklar.
    Ein Datum muss das verlangte Format YYYY-MM-DD haben („30.04.“ ohne Jahr reicht nicht)."""
    if feld.status != "belegt" or not feld.wert:
        return False
    wert = feld.wert.strip().lower()
    if any(f in wert for f in _FUELLSAETZE):
        return True
    return feld.name == "datum" and not _DATUM.fullmatch(feld.wert.strip())


def _vorschlag(
    datei: Datei,
    kategorie: str | None,
    typ: str | None,
    felder: tuple[Feld, ...],
    zielname: str | None,
    ocr_unsicher: bool,
    begruendung: str,
) -> Vorschlag:
    return Vorschlag(
        datei_hash=datei.hash,
        datei_name=datei.name,
        kategorie=kategorie,
        typ=typ,
        felder=felder,
        zielname=zielname,
        status=_status(kategorie, typ, felder, zielname, ocr_unsicher),
        begruendung=begruendung,
    )


def _offene_felder(profil: Profil) -> tuple[Feld, ...]:
    return tuple(Feld(name=n, wert=None, beleg=None, status="unklar") for n in profil.felder)


# 2.400 Woerter. Der fruehere Kommentar hier ("~3.000 Tokens: passt in Ollamas 4.096-Standardkontext") war
# falsch: nachgemessen am 30-Seiten-Rahmenvertrag (24.09.2026) ergibt dieses Budget einen Prompt von 19.160
# Zeichen plus 1.557 Zeichen Schema, zusammen rund 6.278 Tokens -- deutsche Texte brauchen etwa 3,3 Zeichen je
# Token, und die Fundstellen-IDs im Schema kommen dazu. Bei num_ctx 4096 kuerzte Ollama davon still ein
# Drittel weg; das Dokument wurde "unklar" und war damit fuer jede Suche unsichtbar. Deshalb steht in
# modelle.yaml jetzt `kontext: 16384` (gemessen: 16/20 -> 18/20 Fragen). Wer das Budget aendert, rechnet die
# Tokenzahl neu -- oder misst sie, wie hier geschehen.
MAX_WOERTER_STANDARD = 2400


def _im_budget(fundstellen: tuple[Fundstelle, ...], max_woerter: int) -> tuple[Fundstelle, ...]:
    """Die ersten Absätze bis zum Wortbudget — die tragen Aussteller, Datum, Nummer, Betrag.

    Ollama kürzt einen zu langen Prompt STILL (kein Fehler): Ein 30-Seiten-Vertrag kam als
    Fragment beim Modell an und wurde mal sicher, mal unklar eingeordnet. Lieber sichtbar
    weglassen als unsichtbar abschneiden.
    """
    genommen: list[Fundstelle] = []
    woerter = 0
    for f in fundstellen:
        n = len(f.text.split())
        if genommen and woerter + n > max_woerter:
            break
        genommen.append(f)
        woerter += n
    return tuple(genommen)


def ordne_ein(
    datei: Datei,
    fundstellen: tuple[Fundstelle, ...],
    profil: Profil,
    provider: "ModelProvider",
    ocr_unsicher: bool = False,
    max_woerter: int = MAX_WOERTER_STANDARD,
) -> Vorschlag:
    from dokumentenassistent.provider import ProviderFehler

    if not fundstellen:
        return _vorschlag(
            datei, None, None, _offene_felder(profil), None, ocr_unsicher,
            "Keine Fundstellen: kein Text zum Einordnen",
        )

    betrachtet = _im_budget(fundstellen, max_woerter)
    hinweis = (
        f" Nur die ersten {len(betrachtet)} von {len(fundstellen)} Absätzen betrachtet (Kontextbudget)."
        if len(betrachtet) < len(fundstellen) else ""
    )
    try:
        antwort = provider.generate_json(
            _baue_prompt(datei, betrachtet, profil), _schema(betrachtet, profil)
        )
    except ProviderFehler as e:
        return _vorschlag(datei, None, None, _offene_felder(profil), None, ocr_unsicher, str(e) + hinweis)

    kategorie = _aus_profil(antwort.get("kategorie"), profil.kategorien)
    typ = _aus_profil(antwort.get("typ"), profil.dokumenttypen)
    felder = _felder_aus_antwort(antwort, profil, {f.id: f for f in betrachtet})
    zielname = (
        baue_zielname(profil, kategorie, typ, felder, datei.pfad.suffix.lower(), original=datei.pfad.stem)
        if kategorie and typ
        else None
    )
    return _vorschlag(datei, kategorie, typ, felder, zielname, ocr_unsicher, (antwort.get("begruendung") or "") + hinweis)
