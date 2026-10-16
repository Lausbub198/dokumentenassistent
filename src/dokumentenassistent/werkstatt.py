"""Orchestrator: verdrahtet M1–M11 in der Reihenfolge des Nutzerflusses.

Hier steht keine Fachlogik — nur Reihenfolge, Statusübergänge und Protokoll.
Jede Entscheidung, die ein Mensch trifft oder die eine Datei aus dem Stapel
nimmt, landet als Zeile in `protokoll.jsonl`.
"""
from __future__ import annotations

import dataclasses
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from dokumentenassistent.sprache import passt_zur_sprache
from dokumentenassistent.ablage import lege_ab
from dokumentenassistent.auslesen import (
    NichtLesbar,
    OcrEinstellungen,
    OcrNichtVerfuegbar,
    lies_seiten,
)
from dokumentenassistent.einordnen import ordne_ein
from dokumentenassistent.erfassen import erfasse_ordner
from dokumentenassistent.fundstellen import zerlege
from dokumentenassistent.index import Index
from dokumentenassistent.konflikte import entscheide, finde_konflikte
from dokumentenassistent.profil import (
    ProfilFehler,
    lade_profil,
    schlage_profil_vor,
    speichere_profil,
    waehle_stichprobe,
)
from dokumentenassistent.provider import Sucheinstellungen
from dokumentenassistent.suche import VORVERARBEITUNG, pfad_praefix, suche
from dokumentenassistent.typen import (
    Antwort,
    Datei,
    Fundstelle,
    Konflikt,
    Profil,
    Seite,
    Vorschlag,
)

if TYPE_CHECKING:
    from dokumentenassistent.provider import ModelProvider

# fortschritt(erledigt, gesamt, datei_name) — vor jedem Modellaufruf beim Einordnen
Fortschritt = Callable[[int, int, str], None]


class Werkstatt:
    """Ein Arbeitsvorgang über einen Quellordner: erfassen → auslesen → Profil →
    einordnen → entscheiden → freigeben → fragen."""

    def __init__(
        self,
        quelle: Path,
        zielablage: Path,
        provider: ModelProvider,
        arbeitsordner: Path | None = None,
        provider_suche: ModelProvider | None = None,
        sucheinstellungen: Sucheinstellungen | None = None,
        ocr: OcrEinstellungen | None = None,
        seitenuebergreifend: bool = False,
    ) -> None:
        self.quelle = Path(quelle)
        self.zielablage = Path(zielablage)
        self.provider = provider
        # Nur für frage()/suche() — Embeddings bleiben beim Haupt-Provider (self.provider),
        # provider_suche liefert dasselbe Embedding-Modell (lade_provider_suche), sonst
        # passen die Suchvektoren nicht zu den beim Einordnen gespeicherten.
        self.provider_suche = provider_suche
        # Reranker/rerank_k/top_n kommen unverändert aus modelle.yaml; die Werkstatt
        # entscheidet hier nichts, sie reicht durch (Standard = Verhalten vor 23.09.2026).
        self.sucheinstellungen = sucheinstellungen or Sucheinstellungen()
        # Engine, Drehung, Sprache und Schwelle kommen unveraendert aus modelle.yaml
        # (provider.lade_ocr_einstellungen); die Werkstatt entscheidet hier nichts. Die
        # Schwelle reist MIT der Engine, weil sie nur zu ihr passt: Tesseract mittelt
        # Wortkaesten, PaddleOCR Zeilen-Scores. Standard = Verhalten vor dem 24.09.2026.
        self.ocr = ocr or OcrEinstellungen()
        self.seitenuebergreifend = seitenuebergreifend
        self.arbeitsordner =Path(arbeitsordner) if arbeitsordner is not None else self.quelle
        self.index = Index(self.arbeitsordner)
        self._profil: Profil | None = lade_profil(self.profil_pfad) if self.profil_pfad.exists() else None

    @property
    def profil_pfad(self) -> Path:
        return self.arbeitsordner / ".dokumentenassistent" / "profil.yaml"

    @property
    def profil(self) -> Profil | None:
        return self._profil

    @property
    def _dateien(self) -> tuple[Datei, ...]:
        """Erster Fundort je Hash in Verarbeitungsreihenfolge — aus dem Index, überlebt Neustarts."""
        return self.index.dateien()

    @property
    def ocr_unsichere_hashes(self) -> frozenset[str]:
        """Hashes, bei denen mindestens eine Seite unter `self.ocr.schwelle` lag."""
        return frozenset(d.hash for d in self._dateien if self.index.status(d.hash) == "ocr_unsicher")

    # ------------------------------------------------------------------ M2

    def erfassen(self) -> tuple[Datei, ...]:
        """M2 → Index. Zweiter und weitere Fundorte desselben Hashes sind Duplikate."""
        dateien = erfasse_ordner(self.quelle)
        for datei in dateien:
            vorher = self.index.datei(datei.hash)
            if vorher is None:
                self.index.registriere(datei, "unklar")
                continue
            if vorher.pfad == datei.pfad:
                continue  # erneuter Lauf über denselben Ordner
            self.index.registriere_duplikat(datei)
            self.index.protokolliere(
                "duplikat", hash=datei.hash, pfade=[str(vorher.pfad), str(datei.pfad)]
            )
        return dateien

    # ------------------------------------------------------------- M3 + M4

    def auslesen(self, fortschritt: Fortschritt | None = None) -> dict[str, tuple[Fundstelle, ...]]:
        """M3 → M4 → Index. Nicht lesbare Dateien bleiben unklar, der Stapel läuft weiter.

        `fortschritt` meldet VOR jeder Datei — wie bei `einordnen`, und aus demselben Grund:
        OCR ist der teuerste Schritt je Datei, und eine Anzeige, die erst danach umspringt,
        steht die ganze Wartezeit auf dem falschen Namen. Gemessen 24.09.2026: 403 s über
        126 echte Dateien, ohne jede Rückmeldung — bei einem Bestand aus Scans wären das
        Stunden.
        """
        je_datei: dict[str, tuple[Fundstelle, ...]] = {}
        for nummer, datei in enumerate(self._dateien):
            if fortschritt is not None:
                fortschritt(nummer, len(self._dateien), datei.name)
            try:
                seiten = lies_seiten(datei.pfad, self.ocr)
            except (NichtLesbar, OcrNichtVerfuegbar) as fehler:
                self.index.setze_status(datei.hash, "unklar")
                self.index.protokolliere(
                    "nicht_lesbar", hash=datei.hash, name=datei.name, grund=str(fehler)
                )
                continue
            if any(self._ocr_zu_unsicher(seite) for seite in seiten):
                self.index.setze_status(datei.hash, "ocr_unsicher")
            fundstellen = zerlege(datei, seiten,
                                  seitenuebergreifend=self.seitenuebergreifend)
            self.index.ersetze_fundstellen(datei.hash, fundstellen,
                extraktion=tuple((s.nummer, s.extraktor, s.extraktor_version) for s in seiten))
            je_datei[datei.hash] = fundstellen
        self._bette_nach_ein()
        return je_datei

    EMBED_BLOCK = 32

    def _praefixe(self) -> dict[str, str]:
        """Dateihash → Kontext-Präfix (Pfad relativ zur Quelle). Leer, wenn `kontext_praefix: keiner`."""
        if self.sucheinstellungen.kontext_praefix != 'pfad':
            return {}
        raus = {}
        for d in self.index.dateien():
            try:
                rel = str(Path(d.pfad).resolve().relative_to(self.quelle.resolve()))
            except ValueError:
                rel = d.name
            raus[d.hash] = pfad_praefix(rel)
        return raus

    def _vorverarbeitung(self) -> str:
        return VORVERARBEITUNG[self.sucheinstellungen.kontext_praefix]

    def _bette_nach_ein(self) -> None:
        """Embeddings für alles, was noch keine hat — in EINEM Aufruf je Lauf.

        Steht hier und nicht in `freigeben`, weil Auffindbarkeit nicht an der
        Einordnung hängen darf (siehe `Index.durchsuchbare_fundstellen`). Ein zweiter
        Auslese-Lauf bettet nichts doppelt ein. Mit `kontext_praefix: pfad` wird der Pfad-Präfix
        mit eingebettet und die Vektoren unter eigener `vorverarbeitung` gespeichert."""
        from dokumentenassistent.index import validiere_vektoren
        revision = self.provider.embedding_revision()
        vorverarbeitung = self._vorverarbeitung()
        offen = self.index.fundstellen_ohne_embedding(modell_revision=revision, vorverarbeitung=vorverarbeitung)
        if not offen:
            return
        praefixe = self._praefixe()
        # In Blöcken: Das 8B-Embedding brauchte für ~2.000 Chunks rund 38 min, ein einziger Aufruf
        # liefe in `timeout` (900 s) und speicherte nichts. Jeder Block wird sofort gespeichert;
        # ein Abbruch verliert höchstens einen Block, der nächste Lauf macht dort weiter.
        for anfang in range(0, len(offen), self.EMBED_BLOCK):
            block = offen[anfang:anfang + self.EMBED_BLOCK]
            vektoren = self.provider.embed([praefixe.get(f.datei_hash, '') + f.text for f in block])
            validiere_vektoren(vektoren, len(block))
            if self.provider.embedding_revision() != revision:
                raise ValueError('Embedding-Modell während der Berechnung verändert')
            self.index.speichere_embeddings(tuple((f.id, v) for f, v in zip(block, vektoren)),
                modell_revision=revision, erwartete_texte={f.id: f.text for f in block},
                vorverarbeitung=vorverarbeitung)

    def _ocr_zu_unsicher(self, seite: Seite) -> bool:
        return seite.per_ocr and seite.sicherheit is not None and seite.sicherheit < self.ocr.schwelle

    # ------------------------------------------------------------------ M6

    def profil_vorschlagen(self, zweck: str) -> Profil:
        stichprobe = waehle_stichprobe(
            {datei.hash: self.index.fundstellen(datei.hash) for datei in self._dateien}
        )
        return schlage_profil_vor(zweck, stichprobe, self.provider)

    def profil_bestaetigen(self, profil: Profil) -> None:
        speichere_profil(profil, self.profil_pfad)
        self._profil = profil
        self.index.protokolliere(
            "profil_bestaetigt", zweck=profil.zweck, kategorien=list(profil.kategorien)
        )

    # ------------------------------------------------------------- M7 + M9

    def einordnen(
        self,
        fortschritt: Fortschritt | None = None,
        abbruch: threading.Event | None = None,
    ) -> tuple[Vorschlag, ...]:
        """M7 nur für Dateien ohne Vorschlag, dann M9 über alle sicheren, dann Index.

        Nachgelegte Dateien kosten nur ihren eigenen Modellaufruf; bestehende Vorschläge
        und schon entschiedene Konflikte bleiben, wie sie sind. Ein gesetztes `abbruch`
        beendet die Schleife nach der laufenden Datei; was bis dahin entstand, wird
        gespeichert — der nächste Aufruf nimmt den Rest (Wiederaufnahme).

        Jede Datei wird einzeln gespeichert, nicht erst am Ende (Befund 24.09.2026:
        63 Minuten Einordnen am echten Bestand standen 63 Minuten lang nirgends).
        """
        profil = self._fordere_profil()
        bekannt = {v.datei_hash: v for v in self.index.vorschlaege()}
        rohe = self._ordne_offene_ein(bekannt, profil, fortschritt, abbruch)
        neue_konflikte = self._neue_konflikte(rohe)
        strittig = {hash_ for k in neue_konflikte for hash_ in (k.hash_a, k.hash_b)}
        for konflikt in neue_konflikte:
            self.index.speichere_konflikt(konflikt)
        vorschlaege = tuple(
            dataclasses.replace(v, status="konflikt") if v.datei_hash in strittig else v
            for v in rohe
        )
        # Die Schleife hat jede neue Datei schon gespeichert; hier bleibt nur, was der
        # Konfliktdurchgang eben geändert hat (sicher -> konflikt).
        for roh, vorschlag in zip(rohe, vorschlaege):
            if vorschlag != roh:
                self._merke_vorschlag(vorschlag)
        return vorschlaege

    def _ordne_offene_ein(
        self,
        bekannt: dict[str, Vorschlag],
        profil: Profil,
        fortschritt: Fortschritt | None,
        abbruch: threading.Event | None,
    ) -> tuple[Vorschlag, ...]:
        """Bekannte Vorschläge durchreichen, offene Dateien einordnen. `gesamt` zählt
        nur, was wirklich ans Modell geht (ocr_unsicher bekommt keinen Aufruf)."""
        offen = [d for d in self._dateien if d.hash not in bekannt]
        gesamt = sum(1 for d in offen if self.index.status(d.hash) != "ocr_unsicher")
        rohe: list[Vorschlag] = []
        erledigt = 0
        for datei in self._dateien:
            if datei.hash in bekannt:
                rohe.append(bekannt[datei.hash])
                continue
            if abbruch is not None and abbruch.is_set():
                self.index.protokolliere("einordnen_abgebrochen", erledigt=erledigt, gesamt=gesamt)
                break
            geht_ans_modell = self.index.status(datei.hash) != "ocr_unsicher"
            if geht_ans_modell and fortschritt is not None:
                fortschritt(erledigt, gesamt, datei.name)
            vorschlag = self._ordne_ein(datei, profil)
            rohe.append(vorschlag)
            # Sofort auf die Platte: der Konfliktdurchgang danach kann `sicher` noch zu
            # `konflikt` machen und überschreibt diese Zeile dann — aber ein Absturz
            # kostet jetzt nur die laufende Datei statt des ganzen Stapels.
            self._merke_vorschlag(vorschlag)
            erledigt += int(geht_ans_modell)
        return tuple(rohe)

    def _neue_konflikte(self, vorschlaege: tuple[Vorschlag, ...]) -> tuple[Konflikt, ...]:
        """Konfliktkandidaten, die der Index noch nicht kennt — entschiedene bleiben entschieden."""
        bekannt = {k.id for k in self.index.konflikte()}
        kandidaten = finde_konflikte(
            tuple(v for v in vorschlaege if v.status == "sicher"), self._texte_je_datei()
        )
        return tuple(k for k in kandidaten if k.id not in bekannt)

    def _ordne_ein(self, datei: Datei, profil: Profil) -> Vorschlag:
        """Unsichere OCR kommt nie vor das Modell (M7 antwortet dann ohne Modellaufruf).

        Einen `ProviderFehler` bei einer einzelnen Datei wandelt M7 selbst in
        `status="unklar"` mit Begründung — der Stapel läuft deshalb weiter.
        """
        if self.index.status(datei.hash) == "ocr_unsicher":
            return ordne_ein(datei, (), profil, self.provider, ocr_unsicher=True)
        return ordne_ein(datei, self.index.fundstellen(datei.hash), profil, self.provider)

    def _texte_je_datei(self) -> dict[str, str]:
        return {
            datei.hash: "\n".join(f.text for f in self.index.fundstellen(datei.hash))
            for datei in self._dateien
        }

    def _fordere_profil(self) -> Profil:
        if self._profil is None:
            raise ProfilFehler("Kein bestätigtes Profil: erst profil_bestaetigen aufrufen")
        return self._profil

    # ------------------------------------------------------------------ M9

    def entscheide_konflikt(
        self, id: str, entscheidung: str, eigener_wert: str | None = None
    ) -> Konflikt:
        konflikte = {k.id: k for k in self.index.konflikte()}
        if id not in konflikte:
            raise ValueError(f"Unbekannter Konflikt: {id!r}")
        entschieden = entscheide(konflikte[id], entscheidung, eigener_wert)
        self.index.speichere_konflikt(entschieden)
        self._loese_konfliktstatus(entschieden)
        self.index.protokolliere(
            "konflikt_entschieden", id=id, entscheidung=entscheidung, eigener_wert=eigener_wert
        )
        return entschieden

    def _loese_konfliktstatus(self, konflikt: Konflikt) -> None:
        """Beide Seiten werden wieder ablegbar, sobald kein offener Konflikt mehr an ihnen hängt."""
        offen = self._offene_konflikt_hashes()
        for hash_ in (konflikt.hash_a, konflikt.hash_b):
            vorschlag = self._vorschlag(hash_)
            if hash_ in offen or vorschlag is None or vorschlag.status != "konflikt":
                continue
            # kein eigener Protokolleintrag: „konflikt_entschieden" dokumentiert den Übergang
            self.index.speichere_vorschlag(dataclasses.replace(vorschlag, status="sicher"))
            self.index.setze_status(hash_, "sicher")

    def _ersetzte_hashes(self) -> frozenset[str]:
        """Bei Entscheidung „ersetzt" verliert das Dokument mit dem früheren Datum sein
        Zitatrecht in der Suche. Die Datei bleibt abgelegt — nur die Antwort zitiert sie nicht mehr."""
        ersetzt: set[str] = set()
        for k in self.index.konflikte(offen=False):
            if k.entscheidung != "ersetzt":
                continue
            daten = {h: self._datum(h) for h in (k.hash_a, k.hash_b)}
            if all(daten.values()) and daten[k.hash_a] != daten[k.hash_b]:
                ersetzt.add(min(daten, key=daten.get))
        return frozenset(ersetzt)

    def _datum(self, hash_: str) -> str | None:
        vorschlag = self._vorschlag(hash_)
        if vorschlag is None:
            return None
        return next((f.wert for f in vorschlag.felder if f.name == "datum" and f.status == "belegt"), None)

    # --------------------------------------------------------------- Mensch

    def korrigiere(
        self, hash: str, kategorie: str | None = None, zielname: str | None = None
    ) -> Vorschlag:
        alt = self._vorschlag(hash)
        if alt is None:
            raise ValueError(f"Unbekannter Hash: {hash!r}")
        neu = dataclasses.replace(
            alt,
            kategorie=alt.kategorie if kategorie is None else kategorie,
            zielname=alt.zielname if zielname is None else zielname,
            status="sicher",
        )
        self.index.speichere_vorschlag(neu)
        self.index.protokolliere(
            "korrektur",
            hash=hash,
            kategorie=neu.kategorie,
            zielname=neu.zielname,
            quelle="mensch",
        )
        return neu

    # ----------------------------------------------------------- M10 + M11

    def freigeben(self, hashes: tuple[str, ...]) -> tuple[Path, ...]:
        """Nur sichere Vorschläge ohne offenen Konflikt werden kopiert und eingebettet."""
        vorschlaege = {v.datei_hash: v for v in self.index.vorschlaege()}
        for hash_ in hashes:
            if hash_ not in vorschlaege:
                raise ValueError(f"Unbekannter Hash: {hash_!r}")
        offen = self._offene_konflikt_hashes()
        pfade: list[Path] = []
        for hash_ in dict.fromkeys(hashes):  # doppelt übergeben → trotzdem nur eine Kopie
            vorschlag = vorschlaege[hash_]
            if self.index.zielpfad(hash_) is not None:
                self.index.protokolliere("uebersprungen", hash=hash_, name=vorschlag.datei_name, grund="bereits abgelegt")
                continue
            grund = self._grund_uebersprungen(vorschlag, hash_ in offen)
            if grund:
                self.index.protokolliere(
                    "uebersprungen", hash=hash_, name=vorschlag.datei_name, grund=grund
                )
                continue
            pfade.append(self._lege_ab(hash_, vorschlag))
        return tuple(pfade)

    @staticmethod
    def _grund_uebersprungen(vorschlag: Vorschlag, offener_konflikt: bool) -> str:
        if offener_konflikt:
            return "offener Konflikt"
        if vorschlag.status != "sicher":
            return f"Status {vorschlag.status}"
        return ""

    def _lege_ab(self, hash_: str, vorschlag: Vorschlag) -> Path:
        datei = self.index.datei(hash_)
        zielpfad = lege_ab(datei, vorschlag, self.zielablage)
        self.index.markiere_bestaetigt(hash_, zielpfad)
        # Kein Einbetten mehr: das erledigt `auslesen` fuer ALLE Dateien. Ablegen und
        # Auffindbarmachen waren bis 24.09.2026 derselbe Schritt -- deshalb war ein
        # nicht eingeordnetes Dokument unauffindbar.
        self.index.protokolliere(
            "freigabe", hash=hash_, name=vorschlag.datei_name, zielpfad=str(zielpfad)
        )
        return zielpfad

    def frage(self, text: str, *, nur_freigegeben: bool = False) -> Antwort:
        ersetzt = self._ersetzte_hashes()
        provider = self.provider_suche or self.provider
        revision = provider.embedding_revision()
        paare = tuple(
            (f, v) for f, v in self.index.durchsuchbare_fundstellen(modell_revision=revision,
                                                                    vorverarbeitung=self._vorverarbeitung())
            if f.datei_hash not in ersetzt
            and (not nur_freigegeben or self.index.zielpfad(f.datei_hash) is not None)
        )
        e = self.sucheinstellungen
        antwort = suche(
            text,
            paare,
            provider,
            offene_konflikt_hashes=self._offene_konflikt_hashes(),
            top_n=e.top_n,
            reranker=e.reranker,
            rerank_k=e.rerank_k,
            **({"schwelle": e.schwelle} if e.schwelle is not None else {}),
            kontextauswahl=e.kontextauswahl,
            kaskade=e.kaskade,
            kaskade_stufe2=e.kaskade_stufe2,
            kontext_praefix=self._praefixe() or None,
        )
        if provider.embedding_revision() != revision:
            raise ValueError('Embedding-Modell während der Suche verändert')
        sprache = getattr(provider, "sprache", "Deutsch")
        if antwort.text and not passt_zur_sprache(antwort.text, sprache):
            antwort = dataclasses.replace(
                antwort, sprachhinweis=f"Die Antwort ist nicht auf {sprache}. Das Modell hat die Sprachvorgabe "
                                       f"nicht eingehalten; die Belege darunter sind trotzdem geprüft.")
        self.index.protokolliere("frage", frage=text, status=antwort.status)
        return antwort

    # ----------------------------------------------------------- Index-Sicht

    def _merke_vorschlag(self, vorschlag: Vorschlag) -> None:
        self.index.speichere_vorschlag(vorschlag)
        self.index.setze_status(vorschlag.datei_hash, vorschlag.status)
        self.index.protokolliere(
            "vorschlag", hash=vorschlag.datei_hash, name=vorschlag.datei_name, status=vorschlag.status
        )

    def _vorschlag(self, hash_: str) -> Vorschlag | None:
        return next((v for v in self.index.vorschlaege() if v.datei_hash == hash_), None)

    def _offene_konflikt_hashes(self) -> frozenset[str]:
        return frozenset(
            hash_ for k in self.index.konflikte(offen=True) for hash_ in (k.hash_a, k.hash_b)
        )
