"""Erweiterung des Korpus "Malerbetrieb Hoffmann 2025" von 100 auf 200 Dateien.

Gleiche Tupelformen wie texte.py; erzeugen.py hängt diese Listen an die
bestehenden an. Die ersten 100 Dateien bleiben unverändert (texte.py ist
eingefroren). Alles frei erfunden.

Ausgangsrechnungen tragen hier ein neuntes Feld `teil`: None (normale
Rechnung), "1. Teilrechnung"/"2. Teilrechnung" oder
("Schlussrechnung", [Nummern der abzuziehenden Teilrechnungen]).
"""
from __future__ import annotations

# Drei neue Lieferanten (die fünf bestehenden stehen in texte.py)
LIEFERANTEN: dict[str, dict[str, str]] = {
    "tapeten": {
        "name": "Tapeten & Boden Krüger GmbH",
        "adresse": "Weberstraße 21, 12346 Neustadt",
        "kunde": "Kundennummer 2071",
        "schema": "TB-25-{n:03d}",
        "bank": "Volksbank Neustadt, IBAN DE00 0000 0000 0000 0000 66",
    },
    "container": {
        "name": "Containerdienst Nordland GmbH",
        "adresse": "Deponieweg 9, 12349 Nordhafen",
        "kunde": "Kundennummer 88-1204",
        "schema": "CN-2025-{n:04d}",
        "bank": "Sparkasse Nordhafen, IBAN DE00 0000 0000 0000 0000 77",
    },
    "arbeitsschutz": {
        "name": "Arbeitsschutz Peters KG",
        "adresse": "Helmstraße 2, 12345 Neustadt",
        "kunde": "Kundennummer 5150",
        "schema": "AP{n:05d}",
        "bank": "Commerzbank Neustadt, IBAN DE00 0000 0000 0000 0000 88",
    },
}

# (pfad, lieferant, nummer, datum, betreff, positionen, korrektur_zu | None, grund | None)
# Nummern fügen sich lückenlos-monoton in die Folgen aus texte.py ein.
EINGANGSRECHNUNGEN: list[tuple] = [
    # Farben Meister: 9 weitere, damit 20 gesamt
    ("Downloads/Rechnung (17).pdf", "farben", 138, "29.01.2025", "Objekt Lindenallee 14, Neustadt",
     [("Fassadenfarbe Siloxan weiß 15 l", 2, 89.00), ("Fassadenrolle 25 cm", 4, 7.90)], None, None),
    ("Scans/Scan_0118.pdf", "farben", 207, "26.02.2025", "Objekt Hauptstraße 12, Neustadt",
     [("Latexfarbe seidenmatt 10 l", 6, 58.00), ("Abtönfarbe Terracotta 1 l", 3, 9.80), ("Malerkrepp 50 mm", 10, 2.35)], None, None),
    ("Downloads/Rechnung (18).pdf", "farben", 344, "15.04.2025", "Objekt Ringstraße 8, Neustadt, Nachbestellung",
     [("Fassadenfarbe Siloxan weiß 15 l", 4, 79.00), ("Tiefengrund 10 l", 2, 36.50)], None, None),
    ("Scans/Scan_0119.pdf", "farben", 468, "27.05.2025", "Objekt Sportplatzweg 1, Neustadt",
     [("Innenfarbe Premium weiß 12,5 l", 8, 42.90), ("Lackfarbe RAL 6005 2,5 l", 4, 34.90)], None, None),
    ("Downloads/Rechnung (19).pdf", "farben", 655, "24.07.2025", "Objekt Am Anger 8, Neustadt",
     [("Innenfarbe Premium weiß 12,5 l", 10, 42.90), ("Abtönfarbe Gelb 1 l", 6, 9.80), ("Abdeckvlies 1 x 50 m", 2, 18.50)], None, None),
    ("Downloads/Rechnung (20).pdf", "farben", 712, "14.08.2025", "Objekt Ahornstraße 3-5, Neustadt",
     [("Fassadenfarbe Siloxan weiß 15 l", 12, 79.00), ("Treppenhausfarbe scheuerbeständig 12,5 l", 6, 61.50),
      ("Fassadenrolle 25 cm", 4, 7.90)], None, None),
    ("Downloads/Dokument (2).pdf", "farben", 760, "03.09.2025", "Objekt Hauptstraße 12, Neustadt",
     [("Fassadenfarbe Siloxan weiß 15 l", 6, 79.00), ("Tiefengrund 10 l", 3, 36.50)], None, None),
    ("Scans/Scan_0120.pdf", "farben", 873, "21.10.2025", "Objekt Tannenweg 4, Neustadt",
     [("Hallenfarbe grau 15 l", 2, 54.00), ("Bodenbeschichtung 2K grau 10 kg", 2, 96.00)], None, None),
    ("Downloads/download (1).pdf", "farben", 998, "02.12.2025", "Objekt Marktplatz 6, Neustadt",
     [("Vliestapeten-Grundierung 10 l", 2, 31.00), ("Innenfarbe Premium weiß 12,5 l", 3, 42.90)], None, None),
    # Gerüstbau Vogel & Sohn: 2 weitere + 1 Korrektur (Konflikt)
    ("Scans/Scan_0121.pdf", "geruest", 131, "23.06.2025", "Objekt Ahornstraße 3-5, Neustadt",
     [("Fassadengerüst Aufbau und Abbau 520 m²", 1, 3640.00), ("Standzeit je Woche ab Woche 5", 4, 260.00)], None, None),
    ("Downloads/attachment (1).pdf", "geruest", 229, "03.11.2025", "Objekt Hauptstraße 12, Neustadt",
     [("Fassadengerüst Aufbau und Abbau 210 m²", 1, 1470.00), ("Anfahrt Neustadt", 1, 85.00)], None, None),
    ("Downloads/Rechnung (31).pdf", "geruest", 240, "17.11.2025", "Objekt Hauptstraße 12, Neustadt",
     [("Fassadengerüst Aufbau und Abbau 210 m²", 1, 1470.00)],
     229, "Die Anfahrt innerhalb des Vertragsgebiets ist laut Rahmenvertrag § 5 im Grundpreis enthalten."),
    # Werkzeughandel Brandt: 2 weitere
    ("Alt/Scan_0122.pdf", "werkzeug", 1078, "28.03.2025", "Werkstattbedarf",
     [("Tapezierbürste", 3, 6.50), ("Kleisterrührer", 2, 12.40), ("Cuttermesser", 6, 4.90)], None, None),
    ("Downloads/eRechnung_1462.pdf", "werkzeug", 1462, "09.12.2025", "Werkstattbedarf",
     [("Akku-Bohrschrauber 18 V", 1, 189.00), ("Bit-Set 32-teilig", 2, 14.90)], None, None),
    # Autohof Westring: die fehlenden Monate April, Juli, September, Oktober, Dezember
    ("Scans/Scan_0123.pdf", "tank", "04-0097", "30.04.2025", "Tankkarte April 2025",
     [("Diesel 441,3 Liter", 1, 600.17), ("Kartengebühr", 1, 2.50)], None, None),
    ("Downloads/Tankkarte_07.pdf", "tank", "07-0113", "31.07.2025", "Tankkarte Juli 2025",
     [("Diesel 503,7 Liter", 1, 685.03), ("Kartengebühr", 1, 2.50)], None, None),
    ("Scans/Scan_0124.pdf", "tank", "09-0121", "30.09.2025", "Tankkarte September 2025",
     [("Diesel 470,2 Liter", 1, 639.47), ("AdBlue 10 l", 1, 9.90), ("Kartengebühr", 1, 2.50)], None, None),
    ("Downloads/invoice_2025-10.pdf", "tank", "10-0126", "31.10.2025", "Tankkarte Oktober 2025",
     [("Diesel 512,9 Liter", 1, 697.54), ("Kartengebühr", 1, 2.50)], None, None),
    ("Downloads/Doc2.pdf", "tank", "12-0135", "31.12.2025", "Tankkarte Dezember 2025",
     [("Diesel 402,5 Liter", 1, 547.40), ("Kartengebühr", 1, 2.50)], None, None),
    # NeuKom: die fehlenden Monate Februar, Juni, August, Oktober, Dezember (ab Juli 5 Karten)
    ("Scans/Scan_0125.pdf", "telefon", 2, "05.02.2025", "Abrechnung Februar 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 4, 19.90)], None, None),
    ("Downloads/2025-7788-06.pdf", "telefon", 6, "05.06.2025", "Abrechnung Juni 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 4, 19.90)], None, None),
    ("Downloads/Rechnung (32).pdf", "telefon", 8, "05.08.2025", "Abrechnung August 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 5, 19.90)], None, None),
    ("Downloads/Telefon Oktober.pdf", "telefon", 10, "05.10.2025", "Abrechnung Oktober 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 5, 19.90), ("Auslandsverbindungen", 1, 2.73)], None, None),
    ("Downloads/NeuKom_Dez.pdf", "telefon", 12, "05.12.2025", "Abrechnung Dezember 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 5, 19.90)], None, None),
    # Tapeten & Boden Krüger (neu): 4 + 1 Korrektur (Konflikt)
    ("Downloads/Rechnung (33).pdf", "tapeten", 41, "17.02.2025", "Objekt Hauptstraße 12, Neustadt",
     [("Vliestapete uni, Rolle 10,05 m", 8, 24.50), ("Vlieskleber 10 kg", 2, 29.90)], None, None),
    ("Scans/Scan_0126.pdf", "tapeten", 85, "22.05.2025", "Objekt Rosenweg 9, Neustadt",
     [("Raufaser Rolle 33,5 m", 6, 17.90), ("Kleister 1 kg", 4, 6.20)], None, None),
    ("Downloads/Rechnung Krueger.pdf", "tapeten", 97, "02.07.2025", "Objekt Tannenweg 4, Neustadt",
     [("Vliestapete Struktur, Rolle 10,05 m", 5, 26.80), ("Tapetengrund 5 l", 1, 21.00)], None, None),
    ("Downloads/Rechnung (34).pdf", "tapeten", 118, "30.10.2025", "Objekt Marktplatz 6, Neustadt",
     [("Vliestapete uni, Rolle 10,05 m", 10, 24.50), ("Vlieskleber 10 kg", 1, 29.90)], None, None),
    ("Downloads/Unbenannt (2).pdf", "tapeten", 131, "18.11.2025", "Objekt Marktplatz 6, Neustadt",
     [("Vliestapete uni, Rolle 10,05 m", 9, 24.50), ("Vlieskleber 10 kg", 1, 29.90)],
     118, "Eine Rolle Vliestapete wurde doppelt berechnet."),
    # Containerdienst Nordland (neu): 4
    ("Downloads/Rechnung (35).pdf", "container", 312, "28.03.2025", "Objekt Ringstraße 8, Neustadt",
     [("Container 5 m³ Bauschutt, Stellung und Abholung", 1, 245.00), ("Entsorgung Bauschutt, je angefangene Tonne", 3, 38.00)],
     None, None),
    ("Scans/Scan_0127.pdf", "container", 587, "30.06.2025", "Sammelentsorgung Farbreste",
     [("Farbreste und Lösemittel, je 200-l-Fass", 2, 96.00), ("Abholung", 1, 45.00)], None, None),
    ("Downloads/CN-2025-0801.pdf", "container", 801, "29.08.2025", "Objekt Ahornstraße 3-5, Neustadt",
     [("Container 7 m³ Baumischabfall, Stellung und Abholung", 1, 285.00), ("Entsorgung Baumischabfall, je angefangene Tonne", 2, 165.00)],
     None, None),
    ("Downloads/Rechnung (36).pdf", "container", 1093, "28.11.2025", "Jahresabholung Gefahrstoffe",
     [("Altfarben und Verdünner, je 200-l-Fass", 3, 96.00), ("Entsorgungsnachweis", 1, 25.00)], None, None),
    # Arbeitsschutz Peters (neu): 4
    ("Downloads/Rechnung (37).pdf", "arbeitsschutz", 20117, "23.01.2025", "Arbeitskleidung Winter",
     [("Winterjacke Malerweiß", 4, 79.00), ("Bundhose Malerweiß", 8, 34.50)], None, None),
    ("Downloads/AP20488.pdf", "arbeitsschutz", 20488, "12.05.2025", "Persönliche Schutzausrüstung",
     [("Sicherheitsschuhe S3", 4, 68.00), ("Atemschutzmaske FFP2, 50 Stück", 2, 29.00), ("Schutzbrille", 6, 4.90)], None, None),
    ("Downloads/Rechnung (38).pdf", "arbeitsschutz", 20903, "04.09.2025", "Arbeitskleidung Herbst",
     [("Softshelljacke Malerweiß", 4, 64.00), ("T-Shirt Firmenlogo", 12, 11.50)], None, None),
    ("Downloads/Peters_Dez.pdf", "arbeitsschutz", 21240, "02.12.2025", "Handschuhe Jahresbedarf",
     [("Arbeitshandschuhe Nitril Größe 10, 12 Paar", 6, 21.60), ("Knieschoner", 4, 15.90)], None, None),
]

# Zahlungserinnerung zu FM-2025-00801 (Rechnung (11).pdf, 524,31 EUR): gleicher Betrag, kein Konflikt.
MAHNUNG: tuple[str, str] = ("Downloads/Rechnung (21).pdf", """
Farben Meister GmbH, Lackstraße 12, 12345 Neustadt

Zahlungserinnerung
Datum 28.10.2025, Kundennummer 10442
Empfänger: Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt

Sehr geehrte Damen und Herren,

für die Rechnung Nr. FM-2025-00801 vom 23.09.2025 über 524,31 EUR konnten wir bisher keinen
Zahlungseingang feststellen. Sicher haben Sie die Zahlung nur übersehen. Bitte überweisen Sie
den offenen Betrag bis zum 11.11.2025 auf das unten genannte Konto. Sollte sich Ihre Zahlung
mit diesem Schreiben überschnitten haben, betrachten Sie diese Erinnerung als gegenstandslos.

Offener Betrag 524,31 EUR
Mahngebühren werden für diese erste Erinnerung nicht berechnet.

Mit freundlichen Grüßen
Farben Meister GmbH, Buchhaltung
Sparkasse Neustadt, IBAN DE00 0000 0000 0000 0000 11
""")

_WEG = ("WEG Ahornstraße 3-5", "c/o Hausverwaltung Kessler GmbH, Verwalterplatz 9, 12345 Neustadt", "Ahornstraße 3-5, Neustadt")
_KITA = ("Kita Regenbogen gGmbH", "Am Anger 8, 12345 Neustadt", "Am Anger 8, Neustadt")
_OLIVE = ("Restaurant Olivenbaum", "Hauptstraße 12, 12345 Neustadt", "Hauptstraße 12, Neustadt")
_TSV = ("TSV Neustadt 1908 e.V.", "Sportplatzweg 1, 12345 Neustadt", "Sportplatzweg 1, Neustadt")
_NOWAK = ("Familie Nowak", "Birkenweg 12, 12345 Neustadt", "Birkenweg 12, Neustadt")
_WEBER = ("Familie Weber", "Tannenweg 4, 12346 Neustadt", "Tannenweg 4, Neustadt")
_LEHMANN = ("Hausarztpraxis Dr. Lehmann", "Marktplatz 6, 12345 Neustadt", "Marktplatz 6, Neustadt")
_CAFE = ("Café Morgenrot", "Bahnhofstraße 5, 12345 Neustadt", "Bahnhofstraße 5, Neustadt")

POS_OLIVE_GASTRAUM = [("Gastraum Wände und Decke Anstrich, m²", 240, 7.40), ("Holzvertäfelung lackieren, m²", 36, 22.00)]
POS_NOWAK_WOHNUNG = [("Anstrich Wände und Decken, m²", 190, 6.80), ("Türen lackieren, Stück", 4, 95.00)]
POS_CAFE_GASTRAUM = [("Gastraum Anstrich, m²", 110, 8.10), ("Theke lackieren, lfm", 6, 120.00)]
POS_WEBER_DACH = [("Dachschrägen und Wände Anstrich, m²", 140, 7.20), ("Holzbalken lasieren, lfm", 42, 9.50)]
POS_LEHMANN_PRAXIS = [("Wände und Decken spachteln Q3, m²", 150, 9.20), ("Anstrich Latex seidenmatt, m²", 150, 7.40)]
POS_TSV = [("Vereinsheim Innenanstrich, m²", 480, 7.60), ("Umkleiden Anstrich feuchtraumgeeignet, m²", 120, 9.80),
           ("Türen und Zargen lackieren, Stück", 8, 95.00)]
POS_WEG_V1 = [("Fassade reinigen, grundieren, zweifach streichen, m²", 520, 22.40),
              ("Treppenhäuser Anstrich zwei Aufgänge, m²", 430, 8.90), ("Gerüst gemäß Angebot", 1, 4800.00)]
POS_WEG_V2 = POS_WEG_V1 + [("Fensterlaibungen, Stück", 44, 42.00)]
POS_KITA_GRUPPEN = [("Gruppenräume Anstrich, m²", 290, 7.60), ("Türen und Zargen lackieren, Stück", 10, 95.00),
                    ("Zuschlag schadstoffarme Farbe", 1, 150.00)]
POS_OLIVE_FASSADE = [("Fassadenanstrich, m²", 210, 15.20), ("Fensterläden lackieren, Stück", 14, 68.00), ("Gerüst gemäß Angebot", 1, 1900.00)]
POS_KITA_TURN_V1 = [("Turnraum Wände Anstrich, m²", 130, 7.60)]
POS_KITA_TURN_V2 = POS_KITA_TURN_V1 + [("Prallschutz-Sockel lackieren, lfm", 28, 16.00)]

# (pfad, nummer, datum, kunde, kundenadresse, objekt, leistung, positionen, teil)
AUSGANGSRECHNUNGEN: list[tuple] = [
    ("Downloads/2025-113.pdf", "2025-113", "21.02.2025", *_OLIVE, "Gastraum Anstrich und Holzvertäfelung", POS_OLIVE_GASTRAUM, None),
    ("Downloads/Rechnung Nowak.pdf", "2025-114", "21.03.2025", *_NOWAK, "Wohnung streichen, drei Zimmer und Flur", POS_NOWAK_WOHNUNG, None),
    ("Downloads/Rechnung (22).pdf", "2025-115", "28.03.2025", *_CAFE, "Gastraum und Theke", POS_CAFE_GASTRAUM, None),
    ("Downloads/2025-116_Weber.pdf", "2025-116", "25.04.2025", *_WEBER, "Dachgeschoss Ausbau Anstrich", POS_WEBER_DACH, None),
    ("Downloads/Rechnung Lehmann.pdf", "2025-117", "16.05.2025", *_LEHMANN, "Renovierung Praxisräume", POS_LEHMANN_PRAXIS, None),
    ("Downloads/2025-118 TSV.pdf", "2025-118", "23.05.2025", *_TSV, "Vereinsheim Innenanstrich, Abschlag für Leistungen bis 23.05.2025",
     [("Abschlag Vereinsheim Innenanstrich", 1, 3000.00)], "1. Teilrechnung"),
    ("Downloads/Rechnung (23).pdf", "2025-119", "13.06.2025", *_TSV, "Vereinsheim Innenanstrich, Schlussrechnung", POS_TSV,
     ("Schlussrechnung", ["2025-118"])),
    ("Downloads/2025-120.pdf", "2025-120", "20.06.2025", *_WEG, "Fassade und Treppenhäuser, Abschlag für Leistungen bis 20.06.2025",
     [("Abschlag Fassade und Treppenhäuser", 1, 9000.00)], "1. Teilrechnung"),
    ("Downloads/Rechnung (24).pdf", "2025-121", "18.07.2025", *_WEG, "Fassade und Treppenhäuser, Abschlag für Leistungen bis 18.07.2025",
     [("Abschlag Fassade und Treppenhäuser", 1, 8000.00)], "2. Teilrechnung"),
    ("Downloads/Rechnung (25).pdf", "2025-122", "15.08.2025", *_KITA, "Gruppenräume Sommerferien, Abschlag für Leistungen bis 15.08.2025",
     [("Abschlag Gruppenräume", 1, 2500.00)], "1. Teilrechnung"),
    ("Downloads/Rechnung WEG.pdf", "2025-123", "22.08.2025", *_WEG, "Fassade und Treppenhäuser, Schlussrechnung", POS_WEG_V2,
     ("Schlussrechnung", ["2025-120", "2025-121"])),
    ("Downloads/2025-124 Kita.pdf", "2025-124", "29.08.2025", *_KITA, "Gruppenräume Sommerferien, Schlussrechnung", POS_KITA_GRUPPEN,
     ("Schlussrechnung", ["2025-122"])),
    ("Downloads/Rechnung Nowak 2.pdf", "2025-125", "12.09.2025", *_NOWAK, "Balkongeländer und Balkondecke",
     [("Geländer entrosten und lackieren, lfm", 12, 38.00), ("Balkondecke Anstrich, m²", 9, 11.00)], None),
    ("Downloads/2025-126.pdf", "2025-126", "26.09.2025", *_OLIVE, "Fassadenanstrich, Abschlag für Leistungen bis 26.09.2025",
     [("Abschlag Fassadenanstrich", 1, 4000.00)], "1. Teilrechnung"),
    ("Downloads/Rechnung (26).pdf", "2025-127", "24.10.2025", *_OLIVE, "Fassadenanstrich, Schlussrechnung", POS_OLIVE_FASSADE,
     ("Schlussrechnung", ["2025-126"])),
    ("Downloads/Rechnung (27).pdf", "2025-128", "31.10.2025", *_KITA, "Turnraum", POS_KITA_TURN_V2, None),
    ("Downloads/2025-129_Weber.pdf", "2025-129", "07.11.2025", *_WEBER, "Garage Bodenbeschichtung und Wände",
     [("Garagenboden 2K-Beschichtung, m²", 36, 24.00), ("Garagenwände Anstrich, m²", 48, 6.90)], None),
    ("Downloads/Rechnung (28).pdf", "2025-130", "21.11.2025", *_LEHMANN, "Wartezimmer Vliestapete",
     [("Vliestapete tapezieren, m²", 46, 13.50), ("Tapete streichen, m²", 46, 5.20)], None),
    ("Downloads/Rechnung (29).pdf", "2025-131", "28.11.2025", *_WEG, "Kellerabgänge zwei Aufgänge",
     [("Kellerabgänge Anstrich, m²", 96, 12.00)], None),
    ("Downloads/Rechnung Morgenrot Dez.pdf", "2025-132", "19.12.2025", *_CAFE, "Gästetoiletten",
     [("Gästetoiletten Anstrich feuchtraumgeeignet, m²", 38, 9.80), ("Tür lackieren, Stück", 2, 95.00)], None),
]

# (pfad, nummer, datum, kunde, objekt, positionen, hinweis) -- A-2025-020 und A-2025-036 je in zwei Fassungen
ANGEBOTE: list[tuple] = [
    ("Downloads/Angebot Olivenbaum.docx", "A-2025-006", "20.01.2025", _OLIVE[0], _OLIVE[2], POS_OLIVE_GASTRAUM, None),
    ("Downloads/Angebot (3).docx", "A-2025-011", "10.02.2025", _NOWAK[0], _NOWAK[2], POS_NOWAK_WOHNUNG, None),
    ("Downloads/Dokument4.docx", "A-2025-016", "03.03.2025", _CAFE[0], _CAFE[2], POS_CAFE_GASTRAUM, None),
    ("Downloads/Angebot Weber.docx", "A-2025-017", "24.03.2025", _WEBER[0], _WEBER[2], POS_WEBER_DACH, None),
    ("Downloads/Angebot_Praxis.docx", "A-2025-018", "07.04.2025", _LEHMANN[0], _LEHMANN[2], POS_LEHMANN_PRAXIS, None),
    ("Downloads/Angebot TSV Vereinsheim.docx", "A-2025-019", "22.04.2025", _TSV[0], _TSV[2], POS_TSV, None),
    ("Alt/Angebot_Ahornstrasse.docx", "A-2025-020", "05.05.2025", _WEG[0], _WEG[2], POS_WEG_V1, None),
    ("Downloads/Angebot_Ahornstrasse_neu.docx", "A-2025-020", "16.05.2025", _WEG[0], _WEG[2], POS_WEG_V2,
     "Überarbeitete Fassung nach Ortstermin am 14.05.2025, Fensterlaibungen ergänzt."),
    ("Downloads/Angebot Kita.docx", "A-2025-022", "16.06.2025", _KITA[0], _KITA[2], POS_KITA_GRUPPEN, None),
    ("Downloads/Angebot (4).docx", "A-2025-030", "11.08.2025", _OLIVE[0], _OLIVE[2], POS_OLIVE_FASSADE, None),
    ("Alt/Angebot Turnraum.docx", "A-2025-036", "15.09.2025", _KITA[0], _KITA[2], POS_KITA_TURN_V1, None),
    ("Downloads/Angebot Turnraum v2.docx", "A-2025-036", "22.09.2025", _KITA[0], _KITA[2], POS_KITA_TURN_V2,
     "Überarbeitete Fassung, Prallschutz-Sockel auf Wunsch der Leitung ergänzt."),
]

# (pfad, schlecht, zeilen) -- 6 sauber, 4 schlecht
KASSENBELEGE: list[tuple[str, bool, str]] = [
    ("Fotos Handy/IMG_3122.jpg", False, ("Hammer & Nagel Baumarkt\nIndustriering 4, Neustadt\n08.03.2025  09:15\n"
     "Rollerbezug 4x       15,60\nAbdeckfolie 2x        7,90\nMalerkrepp 3x         8,70\n"
     "Summe        32,20 EUR\nenthält 19 % USt 5,14\nBarzahlung")),
    ("Fotos Handy/IMG_3287.jpg", False, ("Autohof Westring\nWestring 200, Neustadt\n22.04.2025  07:41\n"
     "Diesel 55,12 l       86,54\nSumme        86,54 EUR\nenthält 19 % USt 13,82\nEC-Karte")),
    ("Fotos Handy/IMG_3350.jpg", False, ("Bäckerei Lutz\nBahnhofstraße 3, Neustadt\n09.05.2025  06:52\n"
     "Brötchen 8 St.        4,00\nKaffee 3x             7,35\nLaugenstange 2x       3,20\n"
     "Summe        14,55 EUR\nenthält 7 % USt 0,95\nBarzahlung")),
    ("Fotos Handy/PXL_20250704_071233.jpg", False, ("Getränkemarkt Quelle\nIndustriering 6, Neustadt\n04.07.2025  07:12\n"
     "Wasser 12x1 l 3 Kisten 14,97\nPfand 3 Kisten        9,90\n"
     "Summe        24,87 EUR\nenthält 19 % USt 3,97\nEC-Karte")),
    ("Fotos Handy/IMG_3610.jpg", False, ("Hammer & Nagel Baumarkt\nIndustriering 4, Neustadt\n19.08.2025  15:48\n"
     "Spachtelmasse 2x     17,80\nSchleifgitter 10x    11,50\nEimer 5x             16,00\nKabelbinder           3,95\n"
     "Summe        49,25 EUR\nenthält 19 % USt 7,86\nEC-Karte")),
    ("Scans/Beleg Tankstelle Okt.jpg", False, ("Autohof Westring\nWestring 200, Neustadt\n14.10.2025  17:20\n"
     "Diesel 58,40 l       91,69\nAdBlue 10 l          14,90\nSumme       106,59 EUR\nenthält 19 % USt 17,02\nEC-Karte")),
    ("Fotos Handy/IMG_3199.jpg", True, ("Hammer & Nagel Baumarkt\nIndustriering 4, Neustadt\n02.04.2025  11:03\n"
     "Silikon 2x           11,80\nCuttermesser          4,90\nSumme        16,70 EUR\nBarzahlung")),
    ("Fotos Handy/WhatsApp Image 2025-06-27 at 16.40.12.jpg", True, ("Bäckerei Lutz\nBahnhofstraße 3, Neustadt\n"
     "27.06.2025  06:49\nBrötchen 10 St.       5,00\nKaffee 4x             9,80\nSumme        14,80 EUR\nBarzahlung")),
    ("Fotos Handy/IMG_3705.jpg", True, ("Autohof Westring\nWestring 200, Neustadt\n05.09.2025  07:58\n"
     "Diesel 49,80 l       78,19\nSumme        78,19 EUR\nEC-Karte\nVielen Dank")),
    ("Fotos Handy/IMG_3890.jpg", True, ("Getränkemarkt Quelle\nIndustriering 6, Neustadt\n21.11.2025  16:31\n"
     "Wasser 12x1 l 2 Kisten 9,98\nPfand 2 Kisten        6,60\nSumme        16,58 EUR\nEC-Karte")),
]

# (pfad, schlecht, text) -- 4 sauber, 2 schlecht
AUFMASSE: list[tuple[str, bool, str]] = [
    ("Scans/Scan_0128.pdf", False, ("Malerbetrieb Hoffmann GmbH\nAufmaß Fassade und Treppenhäuser\n\nObjekt Ahornstraße 3-5, Neustadt\n"
     "Datum 05.06.2025, aufgenommen von T. Hoffmann\n\nStraßenseite 22,00 x 12,00 m = 264,00 m²\nHofseite 22,00 x 12,00 m = 264,00 m²\n"
     "Abzug Fenster 44 Stück = 8,00 m²\n\nFassade gesamt 520,00 m²\nFensterlaibungen 44 Stück\nTreppenhäuser zwei Aufgänge 430,00 m²")),
    ("Scans/Scan_0129.pdf", False, ("Malerbetrieb Hoffmann GmbH\nAufmaß Gruppenräume\n\nObjekt Am Anger 8, Neustadt\n"
     "Datum 28.07.2025, aufgenommen von K. Maurer\n\nGruppenraum 1: Wände 62 m², Decke 34 m²\nGruppenraum 2: Wände 62 m², Decke 34 m²\n"
     "Gruppenraum 3: Wände 58 m², Decke 30 m²\nFlur: Wände 10 m²\n\nAnstrichfläche gesamt 290 m²\nTüren und Zargen 10 Stück")),
    ("Alt/Scan_0130.pdf", True, ("Malerbetrieb Hoffmann GmbH\nAufmaß Fassade\n\nObjekt Hauptstraße 12, Neustadt\n"
     "Datum 15.09.2025, aufgenommen von T. Hoffmann\n\nStraßenseite 15,00 x 8,00 m = 120,00 m²\nHofseite 15,00 x 8,00 m = 120,00 m²\n"
     "Giebel 2 x 15,00 m² = 30,00 m²\nAbzug Fenster und Türen = 60,00 m²\n\nFassade gesamt 210,00 m²\nFensterläden 14 Stück")),
    ("Scans/Scan_0131.pdf", False, ("Malerbetrieb Hoffmann GmbH\nStundenzettel KW 26 / 2025\n\nMitarbeiter Lukas Fink\n"
     "Baustelle Ahornstraße 3-5, Neustadt\n\nMontag 23.06.     8,0 Std\nDienstag 24.06.   8,0 Std\nMittwoch 25.06.   8,5 Std\n"
     "Donnerstag 26.06. 8,0 Std\nFreitag 27.06.    6,0 Std\n\nSumme Woche 38,5 Std\nUnterschrift Bauleitung T. Hoffmann")),
    ("Scans/Scan_0132.pdf", False, ("Malerbetrieb Hoffmann GmbH\nStundenzettel KW 33 / 2025\n\nMitarbeiter Kevin Maurer\n"
     "Baustelle Am Anger 8, Neustadt\n\nMontag 11.08.     8,0 Std\nDienstag 12.08.   8,0 Std\nMittwoch 13.08.   8,0 Std\n"
     "Donnerstag 14.08. 8,0 Std\nFreitag 15.08.    5,5 Std\n\nSumme Woche 37,5 Std\nUnterschrift Bauleitung T. Hoffmann")),
    ("Scans/Scan_0133.pdf", True, ("Malerbetrieb Hoffmann GmbH\nStundenzettel KW 40 / 2025\n\nMitarbeiter Lukas Fink\n"
     "Baustelle Hauptstraße 12, Neustadt\n\nMontag 29.09.     8,0 Std\nDienstag 30.09.   8,0 Std\nMittwoch 01.10.   8,0 Std\n"
     "Donnerstag 02.10. 8,0 Std\nFreitag 03.10.    Feiertag\n\nSumme Woche 32,0 Std\nUnterschrift Bauleitung T. Hoffmann")),
]

VERSICHERUNG_PFAD = "Downloads/Police.pdf"
VERSICHERUNG_KOPF = """
Nordland Versicherung AG, Assekuranzplatz 1, 12348 Hafenstadt

Versicherungsschein Betriebshaftpflichtversicherung
Versicherungsschein-Nr. BH 4471 0093, ausgestellt am 20.12.2024
Versicherungsnehmerin: Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt
Versicherungsbeginn 01.01.2025
"""

# 12 Paragraphen, je einer pro Seite. Seite 4 (Deckungssumme), 7 (Selbstbeteiligung) und 11 (Kündigung) tragen Sollantworten.
VERSICHERUNG_PARAGRAPHEN: list[tuple[str, str]] = [
    ("§ 1 Versicherungsnehmer", "Versicherungsnehmerin ist die Malerbetrieb Hoffmann GmbH, vertreten durch den Geschäftsführer Thomas Hoffmann."),
    ("§ 2 Versichertes Risiko", "Versichert ist die gesetzliche Haftpflicht aus dem Betrieb eines Maler- und Lackiererbetriebs mit bis zu acht Beschäftigten einschließlich Gerüstnutzung."),
    ("§ 3 Beginn und Dauer", "Der Vertrag beginnt am 01.01.2025 und läuft bis zum 31.12.2027. Er verlängert sich stillschweigend um jeweils ein Jahr."),
    ("§ 4 Deckungssummen", "Die Deckungssumme beträgt je Versicherungsfall 5.000.000 Euro pauschal für Personen- und Sachschäden sowie 250.000 Euro für Vermögensschäden, höchstens das Zweifache je Versicherungsjahr."),
    ("§ 5 Beitrag", "Der Jahresbeitrag beträgt 1.860,00 Euro einschließlich Versicherungsteuer und ist jeweils zum 01.01. im Voraus fällig."),
    ("§ 6 Obliegenheiten", "Die Versicherungsnehmerin zeigt Änderungen der Beschäftigtenzahl und neue Tätigkeitsfelder innerhalb eines Monats an."),
    ("§ 7 Selbstbeteiligung", "Die Selbstbeteiligung beträgt 500,00 Euro je Sachschaden. Für Personenschäden wird keine Selbstbeteiligung erhoben."),
    ("§ 8 Tätigkeitsschäden", "Schäden an fremden Sachen, die Gegenstand der Bearbeitung sind, sind bis 100.000 Euro je Versicherungsfall mitversichert."),
    ("§ 9 Mitversicherte Personen", "Mitversichert ist die persönliche gesetzliche Haftpflicht aller Beschäftigten und Auszubildenden aus ihrer Tätigkeit für den Betrieb."),
    ("§ 10 Ausschlüsse", "Nicht versichert sind Schäden durch vorsätzliches Handeln, Vertragsstrafen und Schäden an vom Betrieb gemieteten Kraftfahrzeugen."),
    ("§ 11 Kündigung", "Der Vertrag kann von beiden Seiten mit einer Frist von drei Monaten zum Ende des Versicherungsjahres schriftlich gekündigt werden. Nach einem Schadenfall besteht ein außerordentliches Kündigungsrecht innerhalb eines Monats."),
    ("§ 12 Schlussbestimmungen", "Es gelten die Allgemeinen Versicherungsbedingungen AHB 2024. Hafenstadt, 20.12.2024, Nordland Versicherung AG."),
]

VERSICHERUNG_FUELLER = [
    "Für die Auslegung dieses Paragraphen gelten die Allgemeinen Versicherungsbedingungen in der bei Vertragsschluss gültigen Fassung.",
    "Anzeigen und Erklärungen der Versicherungsnehmerin sind in Textform an die Hauptverwaltung in Hafenstadt zu richten.",
    "Der Versicherer bestätigt jede Änderung des Vertrags durch einen Nachtrag zum Versicherungsschein.",
    "Soweit ein Nachtrag etwas Abweichendes regelt, geht er den Bestimmungen dieses Paragraphen vor.",
]

# (pfad, seiten) -- weitere Verträge
VERTRAEGE: list[tuple[str, list[str]]] = [
    ("Downloads/Wartungsvertrag.pdf", ["""
Werkzeughandel Brandt e.K., Industriestraße 44, 12345 Neustadt

Wartungsvertrag Nr. WV-2025-08 vom 14.02.2025
Auftraggeberin: Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt, Kundennummer 3310
Gegenstand: jährliche Wartung von zwei Airless-Spritzgeräten und einem Staubsauger Klasse M
in der Werkstatt Pinselgasse 5

Laufzeit 01.03.2025 bis 28.02.2027
Wartungspauschale 240,00 EUR netto jährlich zzgl. 19 % USt 45,60 EUR = 285,60 EUR brutto
Fällig jeweils nach der Wartung im März
""", """
Seite 2

Die Wartung umfasst Sichtprüfung, Reinigung, Prüfung der Dichtungen und Filter sowie einen
Funktionstest. Ersatzteile werden nach Aufwand gesondert berechnet.
Kündigung mit einer Frist von drei Monaten zum Laufzeitende.
Neustadt, 14.02.2025, Werkzeughandel Brandt e.K., Malerbetrieb Hoffmann GmbH Thomas Hoffmann
"""]),
    ("Downloads/Mobilfunkvertrag.pdf", ["""
NeuKom Telekommunikation GmbH, Funkweg 7, 12346 Neustadt

Mobilfunk-Rahmenvertrag Nr. MV-7788-2025 vom 26.06.2025
Kundin: Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt, Kundennummer 7788

Leistung: fünf Mobilfunkkarten Business-Tarif mit Telefonflat und 20 GB Datenvolumen je Karte
Monatlicher Grundpreis je Karte 19,90 EUR netto
Einrichtung Zusatzkarte 25,00 EUR netto einmalig
Mindestlaufzeit 24 Monate ab 01.07.2025
""", """
Seite 2

Die Abrechnung erfolgt monatlich mit der bestehenden Festnetz- und Internetrechnung.
Auslandsverbindungen werden nach der Preisliste Business gesondert berechnet.
Kündigungsfrist ein Monat zum Ende der Mindestlaufzeit, danach monatlich.
Neustadt, 26.06.2025, NeuKom Telekommunikation GmbH, Malerbetrieb Hoffmann GmbH
"""]),
    ("Alt/Leasing_2.pdf", ["""
NordLease GmbH, Leasingallee 2, 12348 Hafenstadt

Leasingvertrag Nr. NL-2025-0771 vom 20.02.2025
Leasingnehmerin: Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt
Fahrzeug: Kastenwagen Cargo 30 L1H1, weiß, Erstzulassung 03.03.2025
Amtliches Kennzeichen NS-MH 251

Laufzeit 36 Monate ab 01.03.2025, Laufleistung 20.000 km jährlich
Monatliche Leasingrate 379,00 EUR netto zzgl. 19 % USt 72,01 EUR = 451,01 EUR brutto
Einmalige Sonderzahlung 2.000,00 EUR netto bei Übergabe
""", """
Seite 2

Mehrkilometer werden mit 0,09 EUR netto je Kilometer berechnet, Minderkilometer
mit 0,05 EUR netto je Kilometer vergütet, jeweils bis 10.000 km.
Wartung und Verschleißreparaturen sind nicht enthalten.
Rückgabe am Ende der Laufzeit bei NordLease GmbH in Hafenstadt.
Hafenstadt, 20.02.2025, NordLease GmbH, Malerbetrieb Hoffmann GmbH Thomas Hoffmann
"""]),
]

BEHOERDEN_TEXT: list[tuple[str, list[str]]] = [
    ("Downloads/HWK.pdf", ["""
Handwerkskammer Neustadt, Kammerstraße 9, 12345 Neustadt

Beitragsbescheid 2025
Bescheiddatum 05.03.2025, Betriebsnummer 0000-2107
Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt

Grundbeitrag 2025                                  245,00 EUR
Zusatzbeitrag 2025 auf Gewerbeertrag               167,00 EUR

Gesamtbetrag 412,00 EUR, fällig am 15.04.2025

Rechtsbehelfsbelehrung: Gegen diesen Bescheid kann innerhalb eines Monats
nach Bekanntgabe Widerspruch erhoben werden.
"""]),
    ("Downloads/Bescheid (2).pdf", ["""
Stadt Neustadt, Ordnungsamt, Rathausplatz 1, 12345 Neustadt

Sondernutzungserlaubnis und Gebührenbescheid
Bescheiddatum 02.06.2025, Aktenzeichen 32-2025-0417
Antragstellerin: Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt

Erlaubnis zur Aufstellung eines Fassadengerüsts auf dem Gehweg vor dem Gebäude
Ahornstraße 3-5, Neustadt, im Zeitraum 16.06.2025 bis 22.08.2025.
Auflagen: Auf dem Gehweg bleibt eine Restbreite von mindestens 1,50 m frei. Das Gerüst ist
bei Dunkelheit zu beleuchten. Der Gehweg ist nach Abbau besenrein zu übergeben.

Sondernutzungsgebühr 186,00 EUR, fällig am 30.06.2025
"""]),
]

BEHOERDEN_SCAN: list[tuple[str, str]] = [
    ("Scans/Scan_0134.pdf", ("Landkreis Neustadt\nKfz-Zulassungsstelle, Kreisstraße 2, 12345 Neustadt\n\nGebührenbescheid Zulassung\n"
     "Bescheiddatum 03.03.2025\nVorgangsnummer ZL 2025 03 0412\n\nHalterin Malerbetrieb Hoffmann GmbH\nPinselgasse 5, 12345 Neustadt\n"
     "Kennzeichen NS-MH 251\nKastenwagen Cargo 30, Diesel\n\nGebühr Zulassung 41,40 EUR\nKennzeichenschilder 21,00 EUR\n\n"
     "Gesamtbetrag 62,40 EUR\nBezahlt am 03.03.2025 per EC-Karte")),
]

NOTIZEN: dict[str, str] = {
    "Downloads/Bautagebuch Ahornstrasse.txt": """Bautagebuch Ahornstraße 3-5, WEG, Hausverwaltung Kessler
Bauleitung T. Hoffmann

16.06. Gerüst Vogel aufgebaut, Abnahme mit Vogel senior, Gehweg-Erlaubnis liegt vor.
17.06. Fassade Straßenseite gereinigt, Kreidetest positiv, Tiefengrund zweimal.
20.06. 1. Teilrechnung geschrieben.
23.06.-27.06. Fink und Maurer Fassade Straßenseite erster Anstrich, Wetter trocken.
30.06. Hofseite gereinigt, Container Nordland für Putzreste bestellt.
07.07. Zweiter Anstrich Straßenseite, Fensterlaibungen 44 Stück begonnen.
18.07. Treppenhaus Aufgang 3 fertig, 2. Teilrechnung geschrieben.
28.07.-08.08. Betriebsurlaub, Gerüst bleibt stehen, Planen gesichert.
11.08. Treppenhaus Aufgang 5 begonnen, Farbe nachbestellt bei Farben Meister.
20.08. Abnahme mit Frau Kessler, ein Fensterbrett nachgebessert.
22.08. Gerüst abgebaut, Schlussrechnung geschrieben.
""",
    "Downloads/tagebuch_kita.txt": """Bautagebuch Kita Regenbogen, Am Anger 8
Sommerferien, Leitung Frau Sommer, Schlüssel beim Hausmeister

11.08. Beginn Gruppenraum 1, Möbel in die Mitte, abgedeckt. Maurer und Azubi.
12.08. Gruppenraum 1 Decke und Wände erster Anstrich, schadstoffarme Farbe.
13.08. Gruppenraum 2, Türen ausgehängt, Zargen geschliffen.
14.08. Gruppenraum 2 zweiter Anstrich, Türen lackiert.
15.08. Gruppenraum 3 begonnen, Teilrechnung geschrieben.
18.08.-22.08. Gruppenraum 3 und Flur, Türen zweiter Lackauftrag.
25.08. Abnahme mit Frau Sommer, Wunsch: Turnraum im Herbst, Angebot zusagen.
29.08. Schlussrechnung geschrieben.
""",
    "Downloads/Neues Textdokument (2).txt": """Bautagebuch Restaurant Olivenbaum, Hauptstraße 12, Fassade
Ansprechpartner Herr Kostas, Küche schließt montags

22.09. Gerüst Vogel aufgebaut, Straßenseite. Aufmaß liegt vor: 210 m², 14 Fensterläden.
23.09. Fassade gereinigt, Risse verspachtelt, Tiefengrund einmal.
26.09. Erster Anstrich Straßenseite, Teilrechnung geschrieben.
29.09.-02.10. Hofseite, Fensterläden ausgehängt und in der Werkstatt lackiert.
03.10. Feiertag.
06.10. Zweiter Anstrich beide Seiten, Fensterläden wieder eingehängt.
17.10. Abnahme mit Herrn Kostas, Gerüst freigemeldet.
24.10. Schlussrechnung geschrieben. Gerüstrechnung Vogel prüfen: Anfahrt ist im Rahmenvertrag drin.
""",
    "Alt/bautagebuch_TSV.txt": """Bautagebuch TSV Neustadt 1908, Vereinsheim, Sportplatzweg 1
Ansprechpartner Herr Brandt (Vorstand), Termine nur werktags bis 16 Uhr

12.05. Beginn Saal, Decke abgeklebt, Wände gespachtelt.
13.05.-16.05. Saal erster und zweiter Anstrich, 480 m².
19.05.-23.05. Umkleiden feuchtraumgeeignete Farbe, Türen ausgehängt. 1. Teilrechnung.
02.06.-06.06. Türen und Zargen lackiert, acht Stück, Flur Ausbesserungen.
11.06. Abnahme mit Herrn Brandt, alles in Ordnung.
13.06. Schlussrechnung geschrieben.
""",
}

WIKI: dict[str, str] = {
    "Downloads/wiki_Kundenliste.md": """# Kundenliste 2025

Stand: 20.12.2025, gepflegt von Sabine Roth

| Kunde | Adresse | Ansprechpartner | Aufträge 2025 |
|---|---|---|---|
| Familie Berger | Lindenallee 14, Neustadt | Herr Berger | Fassade Einfamilienhaus |
| Zahnarztpraxis Dr. Petra Winkler | Marktplatz 2, Neustadt | Frau Dr. Winkler | Praxisräume |
| Bäckerei Lutz | Bahnhofstraße 3, Neustadt | Herr Lutz | Verkaufsraum, Fenster |
| Hausverwaltung Kessler GmbH | Verwalterplatz 9, Neustadt | Frau Kessler | Ringstraße 8 Fassade; WEG Ahornstraße 3-5 |
| Ehepaar Schmitz | Rosenweg 9, Neustadt | Frau Schmitz | Tapezierarbeiten |
| Kita Sonnenschein e.V. | Wiesenweg 5, Neustadt | Frau Ahrens | Gruppenräume Sommerferien |
| Autohaus Brenner GmbH | Gewerbering 12, Neustadt | Herr Brenner | Werkstatthalle |
| Wohnungsbau Neustadt eG | Parkstraße 20, Neustadt | Herr Kolbe | Treppenhäuser Parkstraße 20-24 |
| Physiotherapie Aktiv | Hauptstraße 40, Neustadt | Frau Becker | Behandlungsräume |
| Gasthof Zur Linde | Dorfstraße 1, Altdorf | Herr Linde | Fassade, Holzverkleidung |
| Familie Öztürk | Amselweg 7, Neustadt | Frau Öztürk | Kinderzimmer, Schlafzimmer |
| Steuerkanzlei Falk | Kanzleiweg 2, Neustadt | Herr Falk | Büroräume |
| Restaurant Olivenbaum | Hauptstraße 12, Neustadt | Herr Kostas | Gastraum; Fassade (Teil- und Schlussrechnung) |
| Familie Nowak | Birkenweg 12, Neustadt | Frau Nowak | Wohnung; Balkon |
| Café Morgenrot | Bahnhofstraße 5, Neustadt | Frau Morgenrot | Gastraum und Theke; Gästetoiletten |
| Familie Weber | Tannenweg 4, Neustadt | Herr Weber | Dachgeschoss; Garage |
| Hausarztpraxis Dr. Lehmann | Marktplatz 6, Neustadt | Herr Dr. Lehmann | Praxisräume; Wartezimmer Tapete |
| TSV Neustadt 1908 e.V. | Sportplatzweg 1, Neustadt | Herr Brandt | Vereinsheim (Teil- und Schlussrechnung) |
| WEG Ahornstraße 3-5 | c/o Hausverwaltung Kessler | Frau Kessler | Fassade und Treppenhäuser (zwei Teil-, eine Schlussrechnung); Kellerabgänge |
| Kita Regenbogen gGmbH | Am Anger 8, Neustadt | Frau Sommer | Gruppenräume (Teil- und Schlussrechnung); Turnraum |

Rechnungen an die WEG Ahornstraße gehen an die Hausverwaltung Kessler, Rechnungsempfänger bleibt die WEG.
Nicht verwechseln: Zahnarztpraxis Winkler (Marktplatz 2) und Hausarztpraxis Lehmann (Marktplatz 6).
""",
    "Downloads/wiki_Preisliste.md": """# Preisliste 2025 (netto, Richtwerte für Angebote)

Stand: 02.01.2025, verantwortlich: Thomas Hoffmann

## Stundensätze

- Geselle 58,00 EUR, Auszubildender 32,00 EUR, Anfahrt im Stadtgebiet Neustadt frei

## Innen

| Leistung | Einheit | Preis |
|---|---|---|
| Anstrich Wände und Decken, einfacher Untergrund | m² | 6,80 |
| Anstrich Wände und Decken, Büro und Praxis | m² | 7,20 bis 7,60 |
| Anstrich Latex seidenmatt | m² | 7,40 |
| Spachteln Q3 | m² | 9,20 |
| Anstrich feuchtraumgeeignet | m² | 9,80 |
| Tapezieren Raufaser | m² | 11,50 |
| Vliestapete tapezieren | m² | 13,50 |
| Tapete streichen | m² | 5,20 |
| Türen und Zargen lackieren | Stück | 95,00 |
| Holzfenster streichen | Stück | 85,00 |
| Bodenbeschichtung 2K | m² | 24,00 |

## Außen

| Leistung | Einheit | Preis |
|---|---|---|
| Fassade reinigen und grundieren | m² | 6,50 |
| Fassadenanstrich zweifach | m² | 14,80 |
| Fassade komplett (reinigen, grundieren, zweifach streichen) | m² | 22,40 |
| Fassadenanstrich Bestand ohne Grundierung | m² | 15,20 |
| Fensterlaibung | Stück | 42,00 |
| Holzverkleidung lasieren | m² | 19,50 |

Gerüst immer nach Angebot des Gerüstbauers zzgl. Aufschlag. Zuschlag schadstoffarme Farbe bei Kitas pauschal.
""",
    "Alt/urlaubsplan-2025.md": """# Urlaubsplan 2025

Betriebsurlaub 28.07. bis 08.08.2025 für alle. Zusätzlich je Mitarbeiter:

| Mitarbeiter | Urlaub | Bemerkung |
|---|---|---|
| Thomas Hoffmann | 20.10. bis 24.10. | Büro besetzt durch S. Roth |
| Kevin Maurer | 14.04. bis 18.04., 15.09. bis 19.09. | ab 01.03. im Betrieb |
| Lukas Fink | 03.03. bis 07.03., 06.10. bis 10.10. | |
| Jens Wagner | 12.05. bis 23.05. | zwei Wochen |
| Sabine Roth | 08.09. bis 12.09. | ab 01.06. im Betrieb, 25 Stunden |
| Mia Schulz (Auszubildende) | 17.11. bis 21.11. | Berufsschule Blockwochen KW 10, 24, 46 |

Urlaubswünsche bis 31.03. eintragen, Baustellenplanung geht vor. Brückentage nach Absprache.
""",
}
