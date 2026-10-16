"""Feste Texte und Stammdaten des Korpus "Malerbetrieb Hoffmann 2025".

Alles frei erfunden: Firmen, Personen, Adressen, Nummern. IBANs bestehen aus
Nullen. Beträge stehen als Netto-Einzelpreise; Netto/USt/Brutto rechnet
erzeugen.py. Rechnungspositionen: (Bezeichnung, Menge, Einzelpreis netto).
"""
from __future__ import annotations

FIRMA = "Malerbetrieb Hoffmann GmbH"
FIRMA_ADRESSE = "Pinselgasse 5, 12345 Neustadt"
FIRMA_FUSS = (
    "Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt, Geschäftsführer Thomas Hoffmann\n"
    "Amtsgericht Neustadt HRB 00000, USt-IdNr. DE000000000, Volksbank Neustadt IBAN DE00 0000 0000 0000 0000 00"
)

# name, adresse, kundennummer des Malerbetriebs beim Lieferanten, Nummernschema, Bank
LIEFERANTEN: dict[str, dict[str, str]] = {
    "farben": {
        "name": "Farben Meister GmbH",
        "adresse": "Lackstraße 12, 12345 Neustadt",
        "kunde": "Kundennummer 10442",
        "schema": "FM-2025-{n:05d}",
        "bank": "Sparkasse Neustadt, IBAN DE00 0000 0000 0000 0000 11",
    },
    "geruest": {
        "name": "Gerüstbau Vogel & Sohn",
        "adresse": "Am Hafen 3, 12347 Altdorf",
        "kunde": "Kundennummer K-2088",
        "schema": "GV 25/{n:04d}",
        "bank": "Volksbank Altdorf, IBAN DE00 0000 0000 0000 0000 22",
    },
    "werkzeug": {
        "name": "Werkzeughandel Brandt e.K.",
        "adresse": "Industriestraße 44, 12345 Neustadt",
        "kunde": "Kundennummer 3310",
        "schema": "R-25-{n:04d}",
        "bank": "Sparkasse Neustadt, IBAN DE00 0000 0000 0000 0000 33",
    },
    "tank": {
        "name": "Autohof Westring GmbH",
        "adresse": "Westring 200, 12345 Neustadt",
        "kunde": "Tankkarte TKK 55021",
        "schema": "TK-2025-{n}",
        "bank": "Postbank, IBAN DE00 0000 0000 0000 0000 44",
    },
    "telefon": {
        "name": "NeuKom Telekommunikation GmbH",
        "adresse": "Funkweg 7, 12346 Neustadt",
        "kunde": "Kundennummer 7788",
        "schema": "2025-7788-{n:02d}",
        "bank": "Commerzbank Neustadt, IBAN DE00 0000 0000 0000 0000 55",
    },
}

# (pfad, lieferant, nummer, datum, betreff, positionen, korrektur_zu | None, grund | None)
EINGANGSRECHNUNGEN: list[tuple] = [
    ("Downloads/Rechnung.pdf", "farben", 104, "14.01.2025", "Objekt Lindenallee 14, Neustadt",
     [("Innenfarbe Premium weiß 12,5 l", 6, 42.90), ("Abdeckvlies 1 x 50 m", 3, 18.50), ("Malerkrepp 50 mm", 12, 2.35)], None, None),
    ("Downloads/Rechnung (4).pdf", "farben", 231, "12.03.2025", "Objekt Ringstraße 8, Neustadt",
     [("Fassadenfarbe Siloxan weiß 15 l", 10, 89.00), ("Tiefengrund 10 l", 4, 36.50), ("Fassadenrolle 25 cm", 6, 7.90)], None, None),
    ("Downloads/Rechnung (9).pdf", "farben", 298, "28.03.2025", "Objekt Ringstraße 8, Neustadt",
     [("Fassadenfarbe Siloxan weiß 15 l", 10, 79.00), ("Tiefengrund 10 l", 4, 36.50), ("Fassadenrolle 25 cm", 6, 7.90)],
     231, "Rahmenpreis für Fassadenfarbe wurde nicht berücksichtigt."),
    ("Downloads/Dokument.pdf", "farben", 412, "06.05.2025", "Objekt Marktplatz 2, Neustadt",
     [("Latexfarbe seidenmatt 10 l", 5, 58.00), ("Abtönfarbe Ocker 1 l", 4, 9.80)], None, None),
    ("Downloads/Rechnung (7).pdf", "farben", 537, "17.06.2025", "Objekt Wiesenweg 5, Neustadt",
     [("Innenfarbe Premium weiß 12,5 l", 12, 42.90), ("Spachtelmasse 25 kg", 4, 21.40), ("Schleifgitter Körnung 120", 20, 1.15)], None, None),
    ("Downloads/FM-2025-00689.pdf", "farben", 689, "05.08.2025", "Objekt Parkstraße 20-24, Neustadt",
     [("Treppenhausfarbe scheuerbeständig 12,5 l", 14, 61.50), ("Lackfarbe RAL 7016 2,5 l", 6, 34.90)], None, None),
    ("Downloads/Rechnung (11).pdf", "farben", 801, "23.09.2025", "Objekt Dorfstraße 1, Altdorf",
     [("Holzlasur nussbaum 5 l", 8, 47.20), ("Pinselset 3-teilig", 5, 12.60)], None, None),
    ("Downloads/download.pdf", "farben", 954, "18.11.2025", "Lagerbestand",
     [("Innenfarbe Premium weiß 12,5 l", 20, 42.90), ("Abdeckfolie 4 x 5 m", 30, 1.95)], None, None),
    ("Alt/Scan_0099.pdf", "farben", 175, "11.02.2025", "Objekt Marktplatz 2, Neustadt",
     [("Innenfarbe Standard weiß 15 l", 4, 29.90), ("Malerkrepp 30 mm", 10, 1.85)], None, None),
    ("Scans/Scan_0103.pdf", "farben", 602, "09.07.2025", "Objekt Gewerbering 12, Neustadt",
     [("Hallenfarbe grau 15 l", 9, 54.00), ("Markierungsfarbe gelb 5 l", 3, 41.20)], None, None),
    ("Scans/Scan_0115.pdf", "farben", 1021, "10.12.2025", "Objekt Kanzleiweg 2, Neustadt",
     [("Innenfarbe Premium weiß 12,5 l", 7, 42.90), ("Akustikfarbe 10 l", 2, 88.00)], None, None),
    ("Downloads/Rechnung (1).pdf", "geruest", 12, "20.01.2025", "Objekt Lindenallee 14, Neustadt",
     [("Fassadengerüst Aufbau und Abbau 180 m²", 1, 1260.00), ("Standzeit je Woche", 2, 95.00)], None, None),
    ("Downloads/Rechnung_Vogel.pdf", "geruest", 67, "14.04.2025", "Objekt Ringstraße 8, Neustadt",
     [("Fassadengerüst Aufbau und Abbau 420 m²", 1, 2940.00), ("Standzeit je Woche", 6, 210.00)], None, None),
    ("Downloads/Rechnung (6).pdf", "geruest", 81, "30.04.2025", "Objekt Ringstraße 8, Neustadt",
     [("Fassadengerüst Aufbau und Abbau 420 m²", 1, 2940.00), ("Standzeit je Woche ab Woche 5", 2, 210.00)],
     67, "Die ersten vier Wochen Standzeit sind laut Rahmenvertrag im Grundpreis enthalten."),
    ("Downloads/Rechnung (10).pdf", "geruest", 155, "11.08.2025", "Objekt Parkstraße 20-24, Neustadt",
     [("Treppenhausgerüst Aufbau und Abbau", 1, 680.00), ("Standzeit je Woche", 3, 60.00)], None, None),
    ("Downloads/attachment.pdf", "geruest", 203, "02.10.2025", "Objekt Dorfstraße 1, Altdorf",
     [("Fassadengerüst Aufbau und Abbau 260 m²", 1, 1820.00), ("Standzeit je Woche ab Woche 5", 1, 130.00)], None, None),
    ("Scans/Scan_0101.pdf", "geruest", 44, "05.03.2025", "Objekt Bahnhofstraße 3, Neustadt",
     [("Rollgerüst 2 Wochen", 1, 320.00)], None, None),
    ("Scans/Scan_0109.pdf", "geruest", 178, "08.09.2025", "Objekt Hauptstraße 40, Neustadt",
     [("Rollgerüst 1 Woche", 1, 180.00), ("Anlieferung", 1, 45.00)], None, None),
    ("Downloads/Rechnung (2).pdf", "werkzeug", 1002, "09.01.2025", "Werkstattbedarf",
     [("Teleskopstange 2-4 m", 3, 24.90), ("Farbroller-Set 25 cm", 10, 6.40)], None, None),
    ("Downloads/RE_1044.pdf", "werkzeug", 1044, "21.02.2025", "Werkstattbedarf",
     [("Airless-Spritzgerät Düsensatz", 1, 189.00), ("Verlängerungskabel 25 m", 2, 39.90)], None, None),
    ("Downloads/Rechnung (5).pdf", "werkzeug", 1102, "15.05.2025", "Werkstattbedarf",
     [("Exzenterschleifer 125 mm", 2, 149.00), ("Schleifscheiben Körnung 80, 50 Stück", 4, 17.50), ("Staubsauger Klasse M", 1, 429.00)],
     None, None),
    ("Downloads/Unbenannt.pdf", "werkzeug", 1139, "03.06.2025", "Werkstattbedarf",
     [("Exzenterschleifer 125 mm", 1, 149.00), ("Schleifscheiben Körnung 80, 50 Stück", 4, 17.50), ("Staubsauger Klasse M", 1, 429.00)],
     1102, "Ein Exzenterschleifer wurde zurückgesendet."),
    ("Downloads/Rechnung (8).pdf", "werkzeug", 1290, "22.08.2025", "Werkstattbedarf",
     [("Leiter Aluminium 3 x 9 Sprossen", 1, 219.00), ("Arbeitshandschuhe Größe 10, 12 Paar", 2, 21.60)], None, None),
    ("Downloads/Rechnung (12).pdf", "werkzeug", 1417, "04.11.2025", "Werkstattbedarf",
     [("Heißluftgebläse 2000 W", 1, 79.00), ("Spachtel-Set 5-teilig", 4, 14.20), ("Cuttermesser-Klingen 100 Stück", 3, 8.90)], None, None),
    ("Scans/Scan_0105.pdf", "werkzeug", 1201, "10.07.2025", "Werkstattbedarf",
     [("Abklebeband Gewebe 50 m", 24, 4.10), ("Eimer 12 l", 10, 3.20)], None, None),
    ("Scans/Scan_0111.pdf", "werkzeug", 1355, "29.09.2025", "Werkstattbedarf",
     [("Tapeziertisch Aluminium", 1, 89.00), ("Tapezierbürste", 4, 6.50)], None, None),
    ("Downloads/Tankkarte_01.pdf", "tank", "01-0088", "31.01.2025", "Tankkarte Januar 2025",
     [("Diesel 412,6 Liter", 1, 561.14), ("Kartengebühr", 1, 2.50)], None, None),
    ("Downloads/Rechnung (3).pdf", "tank", "03-0091", "31.03.2025", "Tankkarte März 2025",
     [("Diesel 498,2 Liter", 1, 682.53), ("Kartengebühr", 1, 2.50)], None, None),
    ("Downloads/invoice_2025-05.pdf", "tank", "05-0102", "31.05.2025", "Tankkarte Mai 2025",
     [("Diesel 455,0 Liter", 1, 614.25), ("Kartengebühr", 1, 2.50)], None, None),
    ("Downloads/Doc1.pdf", "tank", "08-0117", "31.08.2025", "Tankkarte August 2025",
     [("Diesel 530,4 Liter", 1, 700.13), ("AdBlue 10 l", 2, 9.90), ("Kartengebühr", 1, 2.50)], None, None),
    ("Downloads/Tankkarte_11.pdf", "tank", "11-0130", "30.11.2025", "Tankkarte November 2025",
     [("Diesel 388,9 Liter", 1, 536.68), ("Kartengebühr", 1, 2.50)], None, None),
    ("Scans/Scan_0100.pdf", "tank", "02-0089", "28.02.2025", "Tankkarte Februar 2025",
     [("Diesel 377,1 Liter", 1, 512.86), ("Kartengebühr", 1, 2.50)], None, None),
    ("Scans/Scan_0107.pdf", "tank", "06-0108", "30.06.2025", "Tankkarte Juni 2025",
     [("Diesel 466,8 Liter", 1, 630.18), ("Kartengebühr", 1, 2.50)], None, None),
    ("Downloads/2025-7788-01.pdf", "telefon", 1, "05.01.2025", "Abrechnung Januar 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 4, 19.90)], None, None),
    ("Downloads/Telefon März.pdf", "telefon", 3, "05.03.2025", "Abrechnung März 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 4, 19.90), ("Auslandsverbindungen", 1, 4.12)], None, None),
    ("Downloads/NeuKom_Mai.pdf", "telefon", 5, "05.05.2025", "Abrechnung Mai 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 4, 19.90)], None, None),
    ("Downloads/rechnung_juli.pdf", "telefon", 7, "05.07.2025", "Abrechnung Juli 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 5, 19.90), ("Einrichtung Zusatzkarte", 1, 25.00)], None, None),
    ("Downloads/Rechnung (14).pdf", "telefon", 9, "05.09.2025", "Abrechnung September 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 5, 19.90)], None, None),
    ("Downloads/scan.pdf", "telefon", 11, "05.11.2025", "Abrechnung November 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 5, 19.90), ("Auslandsverbindungen", 1, 1.87)], None, None),
    ("Scans/Scan_0102.pdf", "telefon", 4, "05.04.2025", "Abrechnung April 2025",
     [("Business-Tarif Festnetz und Internet", 1, 59.90), ("Mobilfunk Karte", 4, 19.90)], None, None),
]

# (pfad, nummer, datum, kunde, kundenadresse, objekt, leistung, positionen)
AUSGANGSRECHNUNGEN: list[tuple] = [
    ("Downloads/2025-101_Berger.pdf", "2025-101", "31.01.2025", "Familie Berger", "Lindenallee 14, 12345 Neustadt",
     "Lindenallee 14, Neustadt", "Fassadenanstrich Einfamilienhaus",
     [("Fassade reinigen und grundieren, m²", 180, 6.50), ("Fassadenanstrich zweifach, m²", 180, 14.80), ("Gerüst gemäß Angebot", 1, 1450.00)]),
    ("Downloads/Rechnung Winkler.pdf", "2025-102", "20.02.2025", "Zahnarztpraxis Dr. Petra Winkler", "Marktplatz 2, 12345 Neustadt",
     "Marktplatz 2, Neustadt", "Renovierung Praxisräume",
     [("Wände und Decken spachteln Q3, m²", 210, 9.20), ("Anstrich Latex seidenmatt, m²", 210, 7.40)]),
    ("Downloads/RE-2025-103.pdf", "2025-103", "14.03.2025", "Bäckerei Lutz", "Bahnhofstraße 3, 12345 Neustadt",
     "Bahnhofstraße 3, Neustadt", "Verkaufsraum und Fenster",
     [("Verkaufsraum Anstrich, m²", 95, 8.10), ("Holzfenster streichen, Stück", 6, 85.00)]),
    ("Downloads/2025-104.pdf", "2025-104", "30.04.2025", "Hausverwaltung Kessler GmbH", "Verwalterplatz 9, 12345 Neustadt",
     "Ringstraße 8, Neustadt", "Fassadensanierung Mehrfamilienhaus",
     [("Fassade reinigen, grundieren, zweifach streichen, m²", 420, 22.40), ("Gerüst 6 Wochen gemäß Angebot", 1, 3990.00),
      ("Fensterlaibungen, Stück", 38, 42.00)]),
    ("Downloads/Rechnung Schmitz.pdf", "2025-105", "28.05.2025", "Ehepaar Schmitz", "Rosenweg 9, 12345 Neustadt",
     "Rosenweg 9, Neustadt", "Tapezierarbeiten Wohnzimmer und Flur",
     [("Tapezieren Raufaser, m²", 78, 11.50), ("Raufaser streichen, m²", 78, 5.20)]),
    ("Downloads/2025-106 Kita.pdf", "2025-106", "27.06.2025", "Kita Sonnenschein e.V.", "Wiesenweg 5, 12345 Neustadt",
     "Wiesenweg 5, Neustadt", "Anstrich Gruppenräume in den Sommerferien",
     [("Gruppenräume Anstrich, m²", 340, 7.60), ("Türen und Zargen lackieren, Stück", 12, 95.00), ("Zuschlag schadstoffarme Farbe", 1, 180.00)]),
    ("Downloads/Rechnung (15).pdf", "2025-107", "25.07.2025", "Autohaus Brenner GmbH", "Gewerbering 12, 12345 Neustadt",
     "Gewerbering 12, Neustadt", "Werkstatthalle",
     [("Hallenwände Anstrich, m²", 620, 6.90), ("Bodenmarkierung, lfm", 140, 4.30)]),
    ("Downloads/2025-108_Wohnungsbau.pdf", "2025-108", "29.08.2025", "Wohnungsbau Neustadt eG", "Parkstraße 20, 12345 Neustadt",
     "Parkstraße 20-24, Neustadt", "Treppenhäuser drei Aufgänge",
     [("Treppenhäuser Anstrich, m²", 860, 8.90), ("Handläufe lackieren, Stück", 3, 240.00), ("Treppenhausgerüst", 1, 900.00)]),
    ("Downloads/Rechnung_Physio.pdf", "2025-109", "26.09.2025", "Physiotherapie Aktiv", "Hauptstraße 40, 12345 Neustadt",
     "Hauptstraße 40, Neustadt", "Behandlungsräume",
     [("Behandlungsräume Anstrich, m²", 160, 7.80), ("Sockelleisten streichen, lfm", 90, 3.60)]),
    ("Downloads/2025-110.pdf", "2025-110", "17.10.2025", "Gasthof Zur Linde", "Dorfstraße 1, 12347 Altdorf",
     "Dorfstraße 1, Altdorf", "Fassade und Holzverkleidung",
     [("Fassadenanstrich, m²", 260, 15.20), ("Holzverkleidung lasieren, m²", 48, 19.50), ("Gerüst gemäß Angebot", 1, 2200.00)]),
    ("Downloads/Rechnung (16).pdf", "2025-111", "14.11.2025", "Familie Öztürk", "Amselweg 7, 12345 Neustadt",
     "Amselweg 7, Neustadt", "Kinderzimmer und Schlafzimmer",
     [("Anstrich Wände und Decken, m²", 96, 6.80), ("Decke spachteln, m²", 28, 12.00)]),
    ("Downloads/Rechnung Falk Dez.pdf", "2025-112", "12.12.2025", "Steuerkanzlei Falk", "Kanzleiweg 2, 12345 Neustadt",
     "Kanzleiweg 2, Neustadt", "Büroräume",
     [("Büroräume Anstrich, m²", 210, 7.20), ("Akustikdecke streichen, m²", 60, 9.50)]),
]

# (pfad, nummer, datum, kunde, objekt, positionen, hinweis)
ANGEBOTE: list[tuple] = [
    ("Downloads/Angebot Berger.docx", "A-2025-003", "08.01.2025", "Familie Berger", "Lindenallee 14, Neustadt",
     [("Fassade reinigen und grundieren, m²", 180, 6.50), ("Fassadenanstrich zweifach, m²", 180, 14.80), ("Gerüst", 1, 1450.00)], None),
    ("Downloads/Dokument3.docx", "A-2025-009", "03.02.2025", "Bäckerei Lutz", "Bahnhofstraße 3, Neustadt",
     [("Verkaufsraum Anstrich, m²", 95, 8.10), ("Holzfenster streichen, Stück", 6, 85.00)], None),
    ("Downloads/Angebot_Ringstrasse.docx", "A-2025-014", "21.02.2025", "Hausverwaltung Kessler GmbH", "Ringstraße 8, Neustadt",
     [("Fassade reinigen, grundieren, zweifach streichen, m²", 420, 22.40), ("Gerüst 6 Wochen", 1, 3990.00), ("Fensterlaibungen, Stück", 38, 42.00)],
     None),
    ("Alt/Angebot_final.docx", "A-2025-021", "12.06.2025", "Wohnungsbau Neustadt eG", "Parkstraße 20-24, Neustadt",
     [("Treppenhäuser Anstrich, m²", 860, 8.90), ("Handläufe lackieren, Stück", 3, 240.00), ("Treppenhausgerüst", 1, 900.00)], None),
    ("Downloads/Angebot_final_final2.docx", "A-2025-021", "19.06.2025", "Wohnungsbau Neustadt eG", "Parkstraße 20-24, Neustadt",
     [("Treppenhäuser Anstrich, m²", 860, 8.90), ("Handläufe lackieren, Stück", 3, 240.00), ("Treppenhausgerüst", 1, 900.00),
      ("Kellerabgänge Anstrich, m²", 120, 12.00)], "Überarbeitete Fassung nach Ortstermin am 18.06.2025, Kellerabgänge ergänzt."),
    ("Downloads/Angebot Linde.docx", "A-2025-027", "14.07.2025", "Gasthof Zur Linde", "Dorfstraße 1, Altdorf",
     [("Fassadenanstrich, m²", 260, 15.20), ("Holzverkleidung lasieren, m²", 48, 19.50), ("Gerüst", 1, 2200.00)], None),
    ("Downloads/Angebot (2).docx", "A-2025-033", "02.09.2025", "Physiotherapie Aktiv", "Hauptstraße 40, Neustadt",
     [("Behandlungsräume Anstrich, m²", 160, 7.80), ("Sockelleisten streichen, lfm", 90, 3.60)], None),
    ("Downloads/Angebot Kanzlei.docx", "A-2025-040", "20.10.2025", "Steuerkanzlei Falk", "Kanzleiweg 2, Neustadt",
     [("Büroräume Anstrich, m²", 210, 7.20), ("Akustikdecke streichen, m²", 60, 9.50)], None),
]

# (pfad, schlecht, zeilen) -- Kassenbelege als Handyfoto
KASSENBELEGE: list[tuple[str, bool, str]] = [
    ("Fotos Handy/IMG_2231.jpg", False, ("Hammer & Nagel Baumarkt\nIndustriering 4, Neustadt\n14.02.2025  10:41\n"
     "Silikon Kartusche      5,90\nSchrauben 4x40         8,60\nDübel 8 mm 100 St.    12,95\nAbdeckplane 6x8      19,90\n"
     "Summe        47,35 EUR\nenthält 19 % USt 7,56\nBarzahlung")),
    ("Fotos Handy/IMG_2402.jpg", False, ("Autohof Westring\nWestring 200, Neustadt\n03.04.2025  07:52\n"
     "Diesel 52,34 l       82,14\nSumme        82,14 EUR\nenthält 19 % USt 13,11\nEC-Karte")),
    ("Fotos Handy/IMG_2577.jpg", False, ("Bäckerei Lutz\nBahnhofstraße 3, Neustadt\n16.05.2025  06:58\n"
     "Brötchen 12 St.       6,00\nKaffee 4x             9,80\nCroissant 4x          8,00\n"
     "Summe        23,80 EUR\nenthält 7 % USt 1,56\nBarzahlung")),
    ("Fotos Handy/IMG_2810.jpg", False, ("Hammer & Nagel Baumarkt\nIndustriering 4, Neustadt\n21.07.2025  16:05\n"
     "Malerkrepp 5x        14,50\nRollerbezug 10x      39,00\nAbdeckvlies 2x       41,80\nLeiterfuß 4x         23,30\n"
     "Summe       118,60 EUR\nenthält 19 % USt 18,94\nEC-Karte")),
    ("Fotos Handy/IMG_2240.jpg", True, ("Hammer & Nagel Baumarkt\nIndustriering 4, Neustadt\n27.02.2025  12:17\n"
     "Spachtel 2x          11,80\nSchleifpapier        7,45\nSumme        19,25 EUR\nBarzahlung")),
    ("Fotos Handy/WhatsApp Image 2025-03-14 at 09.12.33.jpg", True, ("Autohof Westring\nWestring 200, Neustadt\n"
     "14.03.2025  08:31\nDiesel 48,10 l       74,07\nSumme        74,07 EUR\nEC-Karte")),
    ("Fotos Handy/IMG_2695.jpg", True, ("Bäckerei Lutz\nBahnhofstraße 3, Neustadt\n20.06.2025  07:03\n"
     "Brötchen 10 St.       5,00\nKaffee 3x             7,35\nSumme        12,35 EUR\nBarzahlung")),
    ("Fotos Handy/IMG_3004.jpg", True, ("Autohof Westring\nWestring 200, Neustadt\n12.09.2025  17:44\n"
     "Diesel 61,02 l       93,36\nAdBlue 10 l          14,90\nSumme       108,26 EUR\nEC-Karte")),
]

# (pfad, schlecht, text) -- Aufmaße und Stundenzettel als Scan
AUFMASSE: list[tuple[str, bool, str]] = [
    ("Scans/Scan_0104.pdf", False, ("Malerbetrieb Hoffmann GmbH\nAufmaß Fassade\n\nObjekt Ringstraße 8, Neustadt\n"
     "Datum 08.04.2025, aufgenommen von T. Hoffmann\n\nNordseite 14,20 x 9,80 m = 139,16 m²\nSüdseite 14,20 x 9,80 m = 139,16 m²\n"
     "Ostseite 7,40 x 9,80 m = 72,52 m²\nWestseite 7,40 x 9,80 m = 72,52 m²\nAbzug Fenster 38 Stück = 3,36 m²\n\n"
     "Fassade gesamt 420,00 m²\nFensterlaibungen 38 Stück")),
    ("Scans/Scan_0108.pdf", False, ("Malerbetrieb Hoffmann GmbH\nAufmaß Treppenhäuser\n\nObjekt Parkstraße 20-24, Neustadt\n"
     "Datum 04.08.2025, aufgenommen von K. Maurer\n\nAufgang 20: Wände 214 m², Decken 72 m²\nAufgang 22: Wände 214 m², Decken 72 m²\n"
     "Aufgang 24: Wände 216 m², Decken 72 m²\n\nAnstrichfläche gesamt 860 m²\nHandläufe 3 Stück")),
    ("Scans/Scan_0113.pdf", True, ("Malerbetrieb Hoffmann GmbH\nAufmaß Fassade\n\nObjekt Dorfstraße 1, Altdorf\n"
     "Datum 29.09.2025, aufgenommen von T. Hoffmann\n\nStraßenseite 16,00 x 7,50 m = 120,00 m²\nHofseite 16,00 x 7,50 m = 120,00 m²\n"
     "Giebel 2 x 10,00 m² = 20,00 m²\n\nFassade gesamt 260,00 m²\nHolzverkleidung 48,00 m²")),
    ("Scans/Scan_0106.pdf", False, ("Malerbetrieb Hoffmann GmbH\nStundenzettel KW 15 / 2025\n\nMitarbeiter Kevin Maurer\n"
     "Baustelle Ringstraße 8, Neustadt\n\nMontag 07.04.     8,0 Std\nDienstag 08.04.   8,5 Std\nMittwoch 09.04.   8,0 Std\n"
     "Donnerstag 10.04. 8,0 Std\nFreitag 11.04.    6,5 Std\n\nSumme Woche 39,0 Std\nUnterschrift Bauleitung T. Hoffmann")),
    ("Scans/Scan_0110.pdf", False, ("Malerbetrieb Hoffmann GmbH\nStundenzettel KW 35 / 2025\n\nMitarbeiter Lukas Fink\n"
     "Baustelle Parkstraße 20-24, Neustadt\n\nMontag 25.08.     8,0 Std\nDienstag 26.08.   8,0 Std\nMittwoch 27.08.   8,0 Std\n"
     "Donnerstag 28.08. 8,0 Std\nFreitag 29.08.    5,0 Std\n\nSumme Woche 37,0 Std\nUnterschrift Bauleitung T. Hoffmann")),
    ("Scans/Scan_0114.pdf", True, ("Malerbetrieb Hoffmann GmbH\nStundenzettel KW 42 / 2025\n\nMitarbeiter Kevin Maurer\n"
     "Baustelle Dorfstraße 1, Altdorf\n\nMontag 13.10.     8,0 Std\nDienstag 14.10.   8,0 Std\nMittwoch 15.10.   9,0 Std\n"
     "Donnerstag 16.10. 8,0 Std\nFreitag 17.10.    4,0 Std\n\nSumme Woche 37,0 Std\nUnterschrift Bauleitung T. Hoffmann")),
]

RAHMENVERTRAG_KOPF = """
Rahmenvertrag über Gerüstbauleistungen

zwischen Gerüstbau Vogel & Sohn, Am Hafen 3, 12347 Altdorf (Auftragnehmer)
und Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt (Auftraggeber)

Vertragsnummer RV-2024-17, geschlossen in Altdorf am 02.12.2024
Gültig ab 01.01.2025
"""

# 30 Paragraphen, je einer pro Seite. Seite 17 und 28 tragen die Sollantworten.
RAHMENVERTRAG_PARAGRAPHEN: list[tuple[str, str]] = [
    ("§ 1 Gegenstand", "Der Auftragnehmer stellt dem Auftraggeber auf Abruf Fassaden-, Treppenhaus- und Rollgerüste für Malerarbeiten im Umkreis von 40 Kilometern um Neustadt zur Verfügung."),
    ("§ 2 Abruf", "Einzelaufträge werden schriftlich oder per E-Mail abgerufen. Der Abruf nennt Objekt, Gerüstart, gewünschte Aufbauwoche und voraussichtliche Standzeit."),
    ("§ 3 Aufbautermin", "Der Auftragnehmer bestätigt den Aufbautermin innerhalb von drei Werktagen. Bei Abrufen mit weniger als zehn Werktagen Vorlauf gilt ein Zuschlag von zehn Prozent auf den Grundpreis."),
    ("§ 4 Grundpreise", "Die Grundpreise je Quadratmeter Gerüstfläche ergeben sich aus der Preisliste in Anlage 1. Sie gelten für das Kalenderjahr 2025."),
    ("§ 5 Anfahrt", "Anfahrten innerhalb des Vertragsgebiets sind im Grundpreis enthalten. Darüber hinaus wird je Kilometer ein Pauschalsatz nach Anlage 1 berechnet."),
    ("§ 6 Gerüstklasse", "Fassadengerüste werden mindestens in Lastklasse 3 gestellt. Abweichende Lastklassen sind im Abruf zu nennen."),
    ("§ 7 Aufbau", "Der Aufbau erfolgt durch Fachpersonal des Auftragnehmers. Der Auftraggeber stellt sicher, dass die Aufstellfläche frei zugänglich und tragfähig ist."),
    ("§ 8 Abnahme", "Nach dem Aufbau wird das Gerüst gemeinsam abgenommen. Das Abnahmeprotokoll ist Bestandteil des Einzelauftrags."),
    ("§ 9 Prüfung", "Der Auftraggeber prüft das Gerüst vor jeder Nutzung auf augenscheinliche Mängel und meldet diese unverzüglich."),
    ("§ 10 Änderungen", "Umbauten am Gerüst führt ausschließlich der Auftragnehmer aus. Eigenmächtige Änderungen durch den Auftraggeber sind untersagt."),
    ("§ 11 Nutzung durch Dritte", "Eine Nutzung des Gerüsts durch Dritte bedarf der schriftlichen Zustimmung des Auftragnehmers."),
    ("§ 12 Verkehrssicherung", "Die Verkehrssicherung im öffentlichen Raum obliegt dem Auftragnehmer, die Genehmigung beschafft der Auftraggeber."),
    ("§ 13 Wetter", "Bei Sturmwarnung ab Windstärke 8 ist das Gerüst nicht zu betreten. Der Auftragnehmer sichert Planen und Netze."),
    ("§ 14 Beleuchtung", "Gerüste an öffentlichen Wegen werden vom Auftragnehmer mit Warnleuchten ausgestattet."),
    ("§ 15 Reinigung", "Der Auftraggeber übergibt das Gerüst besenrein. Grobe Farbverschmutzungen werden nach Aufwand berechnet."),
    ("§ 16 Abbau", "Der Abbau erfolgt innerhalb von fünf Werktagen nach schriftlicher Freimeldung durch den Auftraggeber."),
    ("§ 17 Standzeiten", "Im Grundpreis ist eine Standzeit von vier Wochen ab Abnahme enthalten. Ab der fünften Woche wird jede angefangene Woche mit dem Wochensatz nach Anlage 1 berechnet. Der Wochensatz beträgt 3,5 Prozent der Aufbausumme."),
    ("§ 18 Rechnungsstellung", "Rechnungen werden je Einzelauftrag nach Abbau gestellt. Sie nennen Objekt, Aufbausumme und berechnete Standzeitwochen getrennt."),
    ("§ 19 Zahlung", "Rechnungen sind innerhalb von 21 Tagen ohne Abzug fällig. Bei Zahlung innerhalb von acht Tagen werden zwei Prozent Skonto gewährt."),
    ("§ 20 Preisanpassung", "Preisänderungen für das Folgejahr sind bis zum 30. September schriftlich anzukündigen."),
    ("§ 21 Haftung", "Der Auftragnehmer haftet für Schäden aus fehlerhaftem Aufbau. Der Auftraggeber haftet für Schäden aus unsachgemäßer Nutzung."),
    ("§ 22 Versicherung", "Beide Parteien unterhalten eine Betriebshaftpflichtversicherung mit einer Deckungssumme von mindestens drei Millionen Euro."),
    ("§ 23 Diebstahl", "Der Auftraggeber sichert Zugänge zum Gerüst außerhalb der Arbeitszeit gegen unbefugtes Betreten."),
    ("§ 24 Geheimhaltung", "Preise und Konditionen dieses Vertrags werden vertraulich behandelt."),
    ("§ 25 Subunternehmer", "Der Auftragnehmer darf Subunternehmer nur mit Zustimmung des Auftraggebers einsetzen."),
    ("§ 26 Mindestabnahme", "Eine Mindestabnahme wird nicht vereinbart. Der Auftraggeber ist nicht verpflichtet, Gerüste ausschließlich beim Auftragnehmer zu beziehen."),
    ("§ 27 Kommunikation", "Ansprechpartner sind auf Seiten des Auftragnehmers Herr Vogel senior, auf Seiten des Auftraggebers Herr Hoffmann."),
    ("§ 28 Laufzeit und Kündigung", "Der Vertrag läuft bis zum 31.12.2025 und verlängert sich jeweils um ein Jahr, wenn er nicht mit einer Frist von drei Monaten zum Jahresende schriftlich gekündigt wird."),
    ("§ 29 Schlussbestimmungen", "Änderungen bedürfen der Schriftform. Sollte eine Bestimmung unwirksam sein, bleibt der Vertrag im Übrigen wirksam."),
    ("§ 30 Unterschriften", "Altdorf, 02.12.2024. Für den Auftragnehmer: Heinrich Vogel. Für den Auftraggeber: Thomas Hoffmann."),
]

RAHMENVERTRAG_FUELLER = [
    "Die Parteien stimmen darin überein, dass die Regelungen dieses Paragraphen im Zweifel so auszulegen sind, wie es dem Zweck einer reibungslosen Zusammenarbeit auf der Baustelle am besten entspricht.",
    "Soweit in einem Einzelauftrag etwas Abweichendes vereinbart wird, geht der Einzelauftrag den Bestimmungen dieses Rahmenvertrags vor, sofern die Abweichung schriftlich festgehalten wurde.",
    "Der Auftragnehmer dokumentiert jede Leistung in seinem Bautagebuch und stellt dem Auftraggeber auf Verlangen eine Kopie der betreffenden Seiten zur Verfügung.",
    "Erkennt eine Partei, dass die Einhaltung einer Frist aus diesem Paragraphen gefährdet ist, teilt sie dies der anderen Partei unverzüglich mit und benennt einen neuen Termin.",
    "Mehrkosten, die durch Umstände entstehen, die keine der Parteien zu vertreten hat, werden nach Nachweis geteilt, sofern sie im Einzelfall zweihundert Euro übersteigen.",
    "Die Regelungen dieses Paragraphen gelten für alle Gerüstarten gleichermaßen, soweit nichts Abweichendes bestimmt ist.",
]

# (pfad, seiten) -- weitere Verträge, je Seite ein Textblock
VERTRAEGE: list[tuple[str, list[str]]] = [
    ("Downloads/Leasing.pdf", ["""
NordLease GmbH, Leasingallee 2, 12348 Hafenstadt

Leasingvertrag Nr. NL-2025-0412 vom 24.01.2025
Leasingnehmerin: Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt
Fahrzeug: Kastenwagen Cargo 35 L2H2, weiß, Erstzulassung 31.01.2025
Amtliches Kennzeichen NS-MH 250

Laufzeit 48 Monate ab 01.02.2025, Laufleistung 25.000 km jährlich
Monatliche Leasingrate 489,00 EUR netto zzgl. 19 % USt 92,91 EUR = 581,91 EUR brutto
Einmalige Sonderzahlung 3.000,00 EUR netto bei Übergabe
""", """
Seite 2

Mehrkilometer werden mit 0,09 EUR netto je Kilometer berechnet, Minderkilometer
mit 0,05 EUR netto je Kilometer vergütet, jeweils bis 10.000 km.
Wartung und Verschleißreparaturen sind nicht enthalten.
Rückgabe am Ende der Laufzeit bei NordLease GmbH in Hafenstadt.
Hafenstadt, 24.01.2025, NordLease GmbH, Malerbetrieb Hoffmann GmbH Thomas Hoffmann
"""]),
    ("Downloads/Mietvertrag Lager.pdf", ["""
Mietvertrag über Gewerberaum

Vermieterin: Gewerbepark Neustadt GmbH, Gewerbering 30, 12345 Neustadt
Mieterin: Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt
Mietobjekt: Lagerhalle 4, Gewerbering 30, 12345 Neustadt, 180 m² Hallenfläche
mit Rolltor und 20 m² Büroraum

Mietbeginn 01.01.2025, Laufzeit fünf Jahre bis 31.12.2029
Kaltmiete 1.150,00 EUR monatlich
Betriebskostenvorauszahlung 220,00 EUR monatlich
Gesamtmiete 1.370,00 EUR monatlich zzgl. 19 % USt
""", """
Seite 2

Kaution: drei Kaltmieten, 3.450,00 EUR.
Nutzung: Lagerung von Farben, Werkzeug und Gerüstteilen, Abstellen von zwei
Firmenfahrzeugen in der Halle. Lagerung von Gefahrstoffen nur in den dafür
vorgesehenen Schränken.
Neustadt, 12.12.2024, Gewerbepark Neustadt GmbH, Malerbetrieb Hoffmann GmbH
"""]),
    ("Alt/Arbeitsvertrag_Maurer.pdf", ["""
Arbeitsvertrag

zwischen Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt (Arbeitgeber)
und Kevin Maurer, Feldweg 18, 12345 Neustadt (Arbeitnehmer)

Beginn 01.03.2025, unbefristet, Probezeit sechs Monate
Tätigkeit: Maler und Lackierer, Geselle
Arbeitszeit 39 Stunden wöchentlich
Monatliches Bruttoentgelt 3.150,00 EUR
Urlaub 30 Arbeitstage je Kalenderjahr
""", """
Seite 2

Der Arbeitnehmer erhält Arbeitskleidung und persönliche Schutzausrüstung.
Überstunden werden durch Freizeit ausgeglichen.
Kündigungsfrist in der Probezeit zwei Wochen, danach nach gesetzlicher Regelung.
Neustadt, 14.02.2025, Thomas Hoffmann, Kevin Maurer
"""]),
    ("Downloads/AV_Roth.pdf", ["""
Arbeitsvertrag

zwischen Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt (Arbeitgeber)
und Sabine Roth, Ulmenweg 3, 12346 Neustadt (Arbeitnehmerin)

Beginn 01.06.2025, unbefristet, Probezeit sechs Monate
Tätigkeit: kaufmännische Angestellte, Büro und Rechnungswesen
Arbeitszeit 25 Stunden wöchentlich, Montag bis Freitag vormittags
Monatliches Bruttoentgelt 1.950,00 EUR
Urlaub 30 Arbeitstage je Kalenderjahr
""", """
Seite 2

Die Arbeitnehmerin ist zur Verschwiegenheit über Kunden- und Betriebsdaten
verpflichtet, auch nach Ende des Arbeitsverhältnisses.
Kündigungsfrist in der Probezeit zwei Wochen, danach nach gesetzlicher Regelung.
Neustadt, 12.05.2025, Thomas Hoffmann, Sabine Roth
"""]),
]

BEHOERDEN_TEXT: list[tuple[str, list[str]]] = [
    ("Downloads/Bescheid.pdf", ["""
Stadt Neustadt, Steueramt, Rathausplatz 1, 12345 Neustadt

Gewerbesteuerbescheid 2025, Vorauszahlungen
Bescheiddatum 10.02.2025, Kassenzeichen 4.0812.0077
Steuerpflichtige: Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt

Festgesetzter Gewerbesteuermessbetrag 2.480,00 EUR, Hebesatz 400 v.H.
Gewerbesteuer-Vorauszahlung 2025 insgesamt 9.920,00 EUR
Vierteljährlich 2.480,00 EUR, fällig am 15.02., 15.05., 15.08. und 15.11.2025

Rechtsbehelfsbelehrung: Gegen diesen Bescheid kann innerhalb eines Monats
nach Bekanntgabe Widerspruch erhoben werden.
"""]),
    ("Downloads/Finanzamt.pdf", ["""
Finanzamt Neustadt, Steuerstraße 4, 12345 Neustadt

Bescheid über Vorauszahlungen zur Körperschaftsteuer 2025
Steuernummer 000/000/00000, Bescheiddatum 24.02.2025
Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt

Körperschaftsteuer-Vorauszahlung je Quartal 1.860,00 EUR
Solidaritätszuschlag je Quartal 102,30 EUR
Fällig am 10.03., 10.06., 10.09. und 10.12.2025
Jahresbetrag Körperschaftsteuer 7.440,00 EUR, Solidaritätszuschlag 409,20 EUR
"""]),
    ("Downloads/IHK_2025.pdf", ["""
Industrie- und Handelskammer Neustadt, Kammerplatz 3, 12345 Neustadt

Beitragsbescheid 2025
Bescheiddatum 18.03.2025, Mitgliedsnummer 0000-4471
Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345 Neustadt

Grundbeitrag 2025                                  180,00 EUR
Umlage 2025 auf Gewerbeertrag                        96,40 EUR

Gesamtbetrag 276,40 EUR, fällig am 30.04.2025
"""]),
]

BEHOERDEN_SCAN: list[tuple[str, str]] = [
    ("Scans/Scan_0116.pdf", ("Bau-Berufsgenossenschaft Nordland\nUnfallkasse Bau, Bauhof 1, 12349 Nordhafen\n\n"
     "Beitragsbescheid 2024\nBescheiddatum 22.04.2025\nMitgliedsnummer 000 4471 88\n\nMalerbetrieb Hoffmann GmbH\n"
     "Pinselgasse 5, 12345 Neustadt\n\nEntgeltsumme 2024 186.400,00 EUR\nGefahrtarifstelle Malerarbeiten\n\n"
     "Beitrag 2024 4.312,80 EUR\nFällig am 15.05.2025")),
    ("Scans/Scan_0117.pdf", ("Hauptzollamt Neustadt\nZollstraße 8, 12345 Neustadt\n\nKraftfahrzeugsteuerbescheid\n"
     "Bescheiddatum 12.02.2025\nSteuernummer KFZ 00 1234 5678\n\nHalterin Malerbetrieb Hoffmann GmbH\n"
     "Kennzeichen NS-MH 250\nKastenwagen, Diesel, 2.200 ccm\n\nJahressteuer 312,00 EUR\nEinzug jährlich am 01.03.2025")),
]

NOTIZEN: dict[str, str] = {
    "Downloads/notizen.txt": """Besprechung 13.01.2025, Büro Pinselgasse
Teilnehmer: Thomas Hoffmann, Kevin Maurer, Lukas Fink, Sabine Roth (ab Juni)

- Jahresplanung: Fassaden Berger (Januar), Ringstraße 8 (April), Kita in den Sommerferien
- Neue Tankkarte beim Autohof Westring beantragt, Sammelrechnung monatlich
- Farben Meister: Rahmenpreis Fassadenfarbe 79,00 netto je 15 l gilt ab März
- Leasing Transporter läuft ab Februar, altes Fahrzeug wird verkauft
- Sabine Roth fängt am 01.06. mit 25 Stunden an, kümmert sich um Rechnungen
""",
    "Downloads/Besprechung_Maerz.txt": """Besprechung 10.03.2025, Baustelle Ringstraße 8

Anwesend: Hoffmann, Maurer, Fink, Wagner

Themen
1. Urlaubsplanung 2025: Betriebsurlaub vom 28.07. bis 08.08.2025, alle Mitarbeiter.
   Einzelurlaub bis 31.03. eintragen, Kita-Baustelle muss vor dem Betriebsurlaub fertig sein.
2. Gerüst Ringstraße kommt am 07.04., Vogel bestätigt.
3. Fassadenfarbe: neuer Rahmenpreis prüfen, erste Rechnung war zu hoch.
4. Werkstatt: Staubsauger Klasse M bestellen, Schleifer defekt.
""",
    "Downloads/todo.txt": """TODO
[ ] Korrekturrechnung Farben Meister zur Rechnung FM-2025-00231 anfordern
[x] Gerüst Ringstraße bestellen
[ ] Steuerberater: Unterlagen Gewerbesteuer und Körperschaftsteuer abgeben
[ ] Angebot Wohnungsbau eG nach Ortstermin überarbeiten (Kellerabgänge)
[ ] IHK-Beitrag überweisen bis 30.04.
[ ] Stundenzettel KW 15 einscannen
[x] Arbeitsvertrag Sabine Roth unterschreiben
[ ] Berufsgenossenschaft Beitrag 2024 zahlen bis 15.05.
""",
    "Downloads/Neues Textdokument.txt": """Telefonnotiz 22.04.2025, 14:10
Anruf Frau Kessler (Hausverwaltung Kessler)
Gerüst Ringstraße steht seit 07.04., Mieter beschweren sich über Lärm morgens vor 7 Uhr.
Zusage: Beginn ab sofort 7:30 Uhr. Abnahme Fassade voraussichtlich 28.04.
Rechnung an Hausverwaltung Kessler GmbH, Verwalterplatz 9, mit Objektangabe Ringstraße 8.
""",
}

WIKI: dict[str, str] = {
    "Downloads/wiki_Arbeitsanweisung_Fassade.md": """# Arbeitsanweisung Fassadenanstrich

Stand: 02.01.2025, verantwortlich: Thomas Hoffmann

## 1. Untergrund prüfen

- Kreidetest mit der Hand, Haftzugprobe mit Klebeband.
- Algen und Moos mit Fassadenreiniger entfernen, 24 Stunden trocknen lassen.

## 2. Grundierung

- Normal saugender Untergrund: Tiefengrund einmal auftragen.
- Stark saugender Untergrund (Kreidetest positiv): Tiefengrund zweimal auftragen,
  zweiter Auftrag erst nach vollständiger Trocknung des ersten.

## 3. Anstrich

- Zwei Anstriche Siloxanfarbe, zweiter Anstrich frühestens nach 12 Stunden.
- Nicht unter 5 Grad Celsius und nicht bei direkter Sonne auf der Fläche arbeiten.

## 4. Dokumentation

- Aufmaß vor Beginn, Fotos nach jedem Arbeitsschritt, Stundenzettel täglich.
""",
    "Downloads/wiki_Lieferanten.md": """# Lieferantenliste

| Lieferant | Was | Kundennummer | Zahlungsziel |
|---|---|---|---|
| Farben Meister GmbH, Neustadt | Farben, Lacke, Zubehör | 10442 | 30 Tage, 2 % Skonto bei 10 Tagen |
| Gerüstbau Vogel & Sohn, Altdorf | Gerüste, Rahmenvertrag RV-2024-17 | K-2088 | 21 Tage, 2 % Skonto bei 8 Tagen |
| Werkzeughandel Brandt e.K., Neustadt | Werkzeug, Maschinen | 3310 | 14 Tage |
| Autohof Westring GmbH | Tankkarte, Sammelrechnung monatlich | TKK 55021 | Lastschrift |
| NeuKom Telekommunikation GmbH | Festnetz, Internet, Mobilfunk | 7788 | Lastschrift |

Bestellungen bei Farben Meister immer mit Objektangabe, sonst fehlt sie auf der Rechnung.
""",
    "Alt/wiki-export-abnahme.md": """# Abnahme und Rechnungsstellung

1. Nach Fertigstellung Ortstermin mit dem Kunden, Abnahmeprotokoll unterschreiben lassen.
2. Aufmaß mit dem Angebot abgleichen, Mehrmengen im Protokoll begründen.
3. Rechnung innerhalb von fünf Werktagen nach Abnahme schreiben, Rechnungsnummer
   fortlaufend 2025-101, 2025-102 und so weiter.
4. Zahlungsziel 14 Tage, bei Privatkunden Hinweis auf Handwerkerleistungen in der Rechnung.
5. Kopie der Rechnung in den Ordner Ausgangsrechnungen, Original per Post oder E-Mail.
""",
}

SACHFREMD_PDF: dict[str, list[str]] = {
    "Downloads/Untitled.pdf": ["""
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
Fehlerbehebung: keine Verbindung, Netzwerkkabel am WAN prüfen.
Entsorgung: nicht in den Hausmüll, bei einer kommunalen Sammelstelle
abgeben. Hersteller NetBox Technik, Elektronikweg 1, 45678 Industriehausen
"""],
    "Alt/Speisekarte.pdf": ["""
Gasthof Zur Linde, Dorfstraße 1, Altdorf

Speisekarte

Vorspeisen
Tagessuppe                                          5,50
Kleiner Salat                                       6,90

Hauptgerichte
Schnitzel mit Bratkartoffeln                       16,90
Linsen mit Spätzle und Saitenwürstchen             13,50
Gemüsepfanne mit Kräuterquark                      12,80

Nachspeisen
Apfelstrudel mit Vanillesoße                        6,50

Alle Preise in Euro inklusive Mehrwertsteuer. Küche 11:30 bis 21:00 Uhr.
"""],
}

REZEPT = """Linsen mit Spätzle

Zutaten für 4 Personen
250 g Tellerlinsen, 1 Zwiebel, 1 Karotte, 1 Stück Sellerie, 2 EL Mehl,
2 EL Essig, 1 EL Zucker, 500 g Spätzle, 4 Saitenwürstchen

Zubereitung
1. Linsen mit Gemüse in 1 Liter Wasser 40 Minuten kochen.
2. Mehl in Butter anrösten, mit Linsenbrühe ablöschen, zu den Linsen geben.
3. Mit Essig, Zucker, Salz und Pfeffer abschmecken.
4. Spätzle kochen, Würstchen in den Linsen erhitzen.
"""
