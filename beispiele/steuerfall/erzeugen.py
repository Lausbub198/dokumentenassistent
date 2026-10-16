#!/usr/bin/env python3
"""Erzeugt den synthetischen Beispielkorpus "Steuerfall 2025" in ./Quelle/.

Deterministisch (feste Texte, bytegleiche Ausgabe): ein Lauf schreibt alle 13
Dateien neu. Personen, Firmen, Adressen, Nummern und Beträge sind frei erfunden,
die IBAN ist absichtlich keine gültige. Rollen: ./README.md, Sollwerte:
tests/golden.json. Aufruf: python beispiele/steuerfall/erzeugen.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

QUELLE = Path(__file__).resolve().parent / "Quelle"
SCHRIFTDATEI = "/System/Library/Fonts/Supplemental/Arial.ttf"
SCAN_BREITE, SCAN_HOEHE, SCAN_PX = 1600, 2263, 44  # A4-Verhältnis, OCR-freundlich
FOTO_BREITE, FOTO_PX, FOTO_DREHUNG, FOTO_UNSCHAERFE = 1300, 72, 12, 4


def schrift(px: int) -> ImageFont.FreeTypeFont:
    """Arial, weil die mitgelieferte Pillow-Schrift Umlaute und ß verfälscht."""
    try:
        return ImageFont.truetype(SCHRIFTDATEI, px)
    except OSError:
        return ImageFont.load_default(size=px)


def text_pdf(pfad: Path, seiten: list[str]) -> Path:
    """PDF mit echter Textebene (reportlab), eine Seite je Eintrag."""
    c = canvas.Canvas(str(pfad), pagesize=A4, invariant=1)
    for seite in seiten:
        c.setFont("Helvetica", 11)
        y = 790
        for zeile in seite.strip("\n").split("\n"):
            c.drawString(56, y, zeile)
            y -= 16
        c.showPage()
    c.save()
    return pfad


def _malen(text: str, breite: int, hoehe: int, px: int) -> Image.Image:
    img = Image.new("RGB", (breite, hoehe), "white")
    d = ImageDraw.Draw(img)
    f = schrift(px)
    y = px
    for zeile in text.strip("\n").split("\n"):
        d.text((px, y), zeile, fill="black", font=f)
        y += int(px * 1.55)
    return img


def bild_pdf(pfad: Path, text: str) -> Path:
    """Sauberer Scan: Bild als ganze A4-Seite, ohne Textebene (reportlab = bytegleich)."""
    bild = _malen(text, SCAN_BREITE, SCAN_HOEHE, SCAN_PX)
    c = canvas.Canvas(str(pfad), pagesize=A4, invariant=1)
    c.drawImage(ImageReader(bild), 0, 0, width=A4[0], height=A4[1])
    c.save()
    return pfad


def handyfoto(pfad: Path, text: str) -> Path:
    """Schief und unscharf: Tesseract liefert mittlere Wortkonfidenz unter 60."""
    zeilen = text.strip("\n").count("\n") + 1
    hoehe = 2 * FOTO_PX + zeilen * int(FOTO_PX * 1.55)
    bild = _malen(text, FOTO_BREITE, hoehe, FOTO_PX)
    bild = bild.rotate(FOTO_DREHUNG, fillcolor="white", expand=True)
    # quality 95: bei 85 findet Tesseract mit Standard-PSM gar kein Wort mehr
    bild.filter(ImageFilter.GaussianBlur(FOTO_UNSCHAERFE)).save(pfad, "JPEG", quality=95)
    return pfad


TEXT_DOKUMENTE: dict[str, list[str]] = {
    "Rechnung (2).pdf": ["""
Heizung Sanitär Krause GmbH, Handwerkerweg 8, 12345 Neustadt

Rechnung Nr. 2025-0815
Rechnungsdatum 14.05.2025, Kundennummer 4711
Empfängerin: Andrea Beispiel, Blumenweg 1, 12345 Neustadt
Leistungsort: Musterstraße 3, Wohnung Nord, 12345 Neustadt
Leistung: Reparatur Heizung, ausgeführt am 12.05.2025

Arbeitslohn 3,5 Stunden                           840,00 EUR
Material Umwälzpumpe                              360,00 EUR
Anfahrtspauschale                                  40,00 EUR

Rechnungsbetrag 1.240,00 EUR
Alle Beträge inklusive 19 % Umsatzsteuer.
""", """
Seite 2

Zahlungsbedingungen: zahlbar bis 30.06.2025 ohne Abzug.
Bankverbindung: Volksbank Neustadt, IBAN DE00 0000 0000 0000 0000 00
Die Arbeiten an der Heizungsanlage in der Wohnung Nord wurden
am 12.05.2025 abgenommen. Gewährleistung 24 Monate.
"""],
    "Rechnung (3).pdf": ["""
Heizung Sanitär Krause GmbH, Handwerkerweg 8, 12345 Neustadt

Korrekturrechnung Nr. 2025-0815-K
Rechnungsdatum 02.06.2025
zu Rechnung Nr. 2025-0815 vom 14.05.2025
Empfängerin: Andrea Beispiel, Blumenweg 1, 12345 Neustadt
Leistungsort: Musterstraße 3, Wohnung Nord, 12345 Neustadt
Leistung: Reparatur Heizung, ausgeführt am 12.05.2025
Grund der Korrektur: eingebaut wurde eine günstigere Umwälzpumpe.

Arbeitslohn 3,5 Stunden                           840,00 EUR
Material Umwälzpumpe                              300,00 EUR
Anfahrtspauschale                                  40,00 EUR

Korrigierter Rechnungsbetrag 1.180,00 EUR
Diese Korrekturrechnung ersetzt die Rechnung Nr. 2025-0815.
"""],
    "Dokument1.pdf": ["""
Mietvertrag über Wohnraum

Vermieterin: Andrea Beispiel, Blumenweg 1, 12345 Neustadt
Mieter: Familie Beispiel, vertreten durch Thomas Beispiel
Mietobjekt: Wohnung Nord, Musterstraße 3, 12345 Neustadt
Zweites Obergeschoss rechts, 68 Quadratmeter, drei Zimmer

Mietbeginn 01.03.2022, auf unbestimmte Zeit
Kaltmiete 780,00 EUR monatlich
Betriebskostenvorauszahlung 190,00 EUR monatlich
Gesamtmiete 970,00 EUR monatlich
""", """
Seite 2

Kaution: zwei Monatsmieten der Kaltmiete, 1.560,00 EUR.
Nebenkosten: Heizung, Wasser, Müllabfuhr und Hausreinigung werden
nach Verbrauch oder Fläche abgerechnet.
Die Hausordnung ist Bestandteil dieses Vertrages.
Neustadt, 24.02.2022, Vermieterin Andrea Beispiel, Mieter Thomas Beispiel
"""],
    "Anhang.pdf": ["""
Hausverwaltung Sommer & Partner, Verwaltungsweg 5, 12345 Neustadt

Nebenkostenabrechnung 2024, Objekt Wohnung Süd, Gartenweg 12, Neustadt
Abrechnungszeitraum 01.01.2024 bis 31.12.2024, Datum 28.03.2025

Heizkosten                                        980,50 EUR
Wasser und Abwasser                               412,30 EUR
Müllabfuhr                                        198,60 EUR
Hausreinigung                                     321,00 EUR

Gesamtbetrag 1.912,40 EUR
Geleistete Vorauszahlungen                      1.800,00 EUR
Nachzahlung 112,40 EUR, fällig bis 30.04.2025
"""],
    "Lohnsteuer.pdf": ["""
Muster Technik AG, Werkstraße 22, 12345 Neustadt

Lohnsteuerbescheinigung für 2025, Arbeitnehmerin
Andrea Beispiel, Blumenweg 1, 12345 Neustadt
Beschäftigungszeitraum 01.01.2025 bis 31.12.2025, Steuerklasse 1
Bruttoarbeitslohn 52.000,00 EUR
Einbehaltene Lohnsteuer 9.480,00 EUR, Kirchensteuer 0,00 EUR
Arbeitnehmeranteil Rentenversicherung 4.836,00 EUR
Arbeitnehmeranteil Krankenversicherung 4.316,00 EUR

Steuer-Identifikationsnummer im Beispielkorpus nicht belegt, ausgestellt
am 15.01.2026
"""],
    "Beleg.pdf": ["""
Tierschutzverein Neustadt e.V., Tierheimweg 3, 12345 Neustadt

Zuwendungsbestätigung: wir bestätigen, dass wir am 12.11.2025 eine
Geldzuwendung erhalten haben.
Betrag der Zuwendung 250,00 EUR, in Worten: zweihundertfünfzig Euro
Zuwendende: Andrea Beispiel, Blumenweg 1, 12345 Neustadt
Die Zuwendung wird ausschließlich für satzungsmäßige Zwecke verwendet.

Neustadt, 14.11.2025, Tierschutzverein Neustadt e.V., Vorstand
"""],
    "Versicherung_2025.pdf": ["""
Nordstern Versicherung, Seeufer 9, 12345 Neustadt

Beitragsrechnung 2025, Privat-Haftpflichtversicherung
Versicherungsschein-Nr. PH-2025-44810, Rechnungsdatum 08.01.2025
Versicherungsnehmerin: Andrea Beispiel, Blumenweg 1, 12345 Neustadt
Versicherungsjahr 01.02.2025 bis 31.01.2026
Deckungssumme 10.000.000 EUR pauschal
Jahresbeitrag 89,50 EUR, Zahlungsweise jährlich, fällig am 01.02.2025
Der Betrag wird per SEPA-Lastschrift eingezogen.
"""],
    "Hausgeld.pdf": ["""
Immo Verwalt GmbH, WEG-Verwaltung, Verwalterplatz 2, 12345 Neustadt

Hausgeldabrechnung 2024, Wohnungseigentum Nr. 7
Wohnung Nord, Musterstraße 3, 12345 Neustadt
Eigentümerin Andrea Beispiel
Abrechnungszeitraum 01.01.2024 bis 31.12.2024, Datum 15.04.2025

Instandhaltungsrücklage                           720,00 EUR
Betriebskosten                                  1.140,00 EUR
Verwaltergebühr                                   480,00 EUR

Gezahltes Hausgeld 195,00 EUR monatlich
Jahresbetrag 2.340,00 EUR
"""],
    "Untitled.pdf": ["""
NetBox 3000, WLAN-Router, Bedienungsanleitung

Lieferumfang: NetBox 3000, Steckernetzteil 12 V / 1,5 A, Kurzanleitung.
Anschlüsse: 1x WAN (RJ45), 4x LAN (RJ45), 1x USB 3.0, 1x Reset.
Erste Inbetriebnahme
1. Netzteil anschließen, die Betriebsanzeige leuchtet weiß.
2. Warten, bis die WLAN-Anzeige dauerhaft leuchtet, dann mit dem
   Netzwerknamen von der Geräteunterseite verbinden.
3. Im Browser die Geräteoberfläche öffnen, Startkennwort eingeben.

Technische Daten: WLAN 802.11ax, 2,4 und 5 GHz, bis 2400 Mbit/s.
""", """
Seite 2

Zurücksetzen auf Werkseinstellungen: Reset-Taste mit einer Büroklammer
10 Sekunden halten, bis alle Anzeigen blinken. Dauer etwa 90 Sekunden.
Anzeigen: Betrieb weiß Gerät bereit, Betrieb blinkt Startvorgang,
WLAN aus Funknetz abgeschaltet, Internet rot keine Verbindung.

Fehlerbehebung: keine Verbindung, Netzwerkkabel am WAN prüfen.
Geringe Reichweite, Gerät frei aufstellen, Abstand zu Metallflächen
und Mikrowellen einhalten. Kein Zugriff, Gerät zurücksetzen.

Entsorgung: nicht in den Hausmüll, bei einer kommunalen Sammelstelle
abgeben. Hersteller NetBox Technik, Elektronikweg 1, 45678 Industriehausen
"""],
}

SCANS: dict[str, str] = {
    "Scan_0043.pdf": """
Heizung Sanitär Krause GmbH
Handwerkerweg 8, 12345 Neustadt

Rechnung Nr. 2025-0815
Rechnungsdatum 14.05.2025

Leistungsort
Musterstraße 3, Wohnung Nord

Leistung
Reparatur Heizung am 12.05.2025

Rechnungsbetrag 1.240,00 EUR

Zahlbar bis 30.06.2025
""",
    "Scan_0044.pdf": """
Stadt Neustadt
Amt für Finanzen

Grundsteuerbescheid 2025
Bescheiddatum 20.01.2025
Aktenzeichen GS-2025-0731

Steuerpflichtige
Andrea Beispiel, Blumenweg 1

Grundstück
Gartenweg 12, Wohnung Süd

Jahresbetrag 412,00 EUR

Vier Teilbeträge von je 103,00 EUR
""",
}

QUITTUNG = """
Hammer & Nagel Baumarkt
Industriering 4, Neustadt
09.07.2025  14:32
Silikon Kartusche      5,90
Dichtungsband          3,40
Schrauben 4x40         8,60
Summe        17,90 EUR
Barzahlung
"""


def main() -> None:
    QUELLE.mkdir(parents=True, exist_ok=True)
    for name, seiten in TEXT_DOKUMENTE.items():
        text_pdf(QUELLE / name, seiten)
    for name, text in SCANS.items():
        bild_pdf(QUELLE / name, text)
    handyfoto(QUELLE / "IMG_8831.jpg", QUITTUNG)
    shutil.copyfile(QUELLE / "Dokument1.pdf", QUELLE / "Dokument1 Kopie.pdf")
    for pfad in sorted(QUELLE.iterdir()):
        print(f"{pfad.name:24s} {pfad.stat().st_size:>8d} Byte")


if __name__ == "__main__":
    main()
