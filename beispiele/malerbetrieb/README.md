# Belastungskorpus „Malerbetrieb Hoffmann 2025"

Synthetischer Eingangsordner mit **genau 200 Dateien** für Lasttests und die
Stufen-Demo. Der Fall: Malerbetrieb Hoffmann GmbH, Pinselgasse 5, 12345
Neustadt, Inhaber Thomas Hoffmann, sechs Mitarbeiter. Zweck laut Profil:
*„Alle Unterlagen des Geschäftsjahres 2025 für Buchhaltung und Steuerberater
ordnen."*

**Alles frei erfunden.** Keine echten Firmen, Personen, Adressen, Kennzeichen
oder Kontonummern. Alle IBANs bestehen aus Nullen und sind ungültig.

Der Korpus ist in zwei Ausbaustufen entstanden: **Dateien 1–100** (`texte.py`,
eingefroren — bytegleich mit dem ersten Commit, Sollwerte, Stufen 10/25/50/100
und Fragen 1–12 unverändert gültig) und **Dateien 101–200** (`texte2.py`), die
den Bestand nicht nur größer, sondern *ähnlicher* machen: 20 Rechnungen eines
Lieferanten, 12 fast gleichlautende Telefonrechnungen, zwei Kitas, zwei Praxen
am Marktplatz, Teil- und Schlussrechnungen zum selben Auftrag, eine
Zahlungserinnerung mit dem Text einer Rechnung. Leitfrage der Erweiterung: ab
wann verwechselt das Werkzeug ähnliche Dokumente, und findet die Suche bei
~650 Absätzen noch die richtige von vielen gleichartigen Rechnungen?

## Erzeugen

```bash
uv run python beispiele/malerbetrieb/erzeugen.py
```

Deterministisch: feste Texte in `texte.py` (1–100) und `texte2.py` (101–200),
keine Zufallswerte, reportlab `invariant=1`, feste Zip-Zeitstempel in den
DOCX — bytegleiche Ausgabe bei jedem Lauf. Der Lauf löscht `Quelle/` und
schreibt alle 200 Dateien neu (8,4 MB, 277 Seiten nach `auslesen.lies_seiten`).
Sollwerte je Datei, Konflikte, Fragen und Stufen: `golden.json`
(Schlüssel = Dateiname, Feld `pfad` = Unterordner).

## Ablagestruktur

Vier Unterordner wie ein echter Rechner: `Alt/` (13), `Downloads/` (132),
`Fotos Handy/` (18), `Scans/` (37). Die Namen sind absichtlich kryptisch
(`Rechnung (4).pdf`, `Unbenannt.pdf`, `Dokument3.docx`, `IMG_2231.jpg`,
`WhatsApp Image 2025-03-14 at 09.12.33.jpg`, `scan.pdf` — ein Text-PDF;
`Rechnung (21).pdf` — die Zahlungserinnerung). Der Assistent darf aus dem
Namen nichts ableiten.

## Bestand (Dateien 1–100)

| Anzahl | Art | Format | Besonderheit |
|---|---|---|---|
| 30 | Lieferantenrechnungen (Farben, Gerüst, Werkzeug, Kraftstoff, Telefon) | PDF, Textebene | 5 Lieferanten mit eigenem Nummernschema, darunter 3 Korrekturrechnungen |
| 10 | Lieferantenrechnungen | Bild-PDF, sauber | keine Textebene → OCR |
| 8 | Kassenbelege (Baumarkt, Tanken, Bäcker) | JPG Handyfoto | 4 sauber, 4 schief + unscharf |
| 12 | Ausgangsrechnungen an Kunden | PDF, Textebene | Nr. 2025-101 … 2025-112, Objektadresse, Leistung |
| 8 | Angebote | DOCX | A-2025-021 in zwei Fassungen mit anderem Betrag |
| 6 | Aufmaße / Stundenzettel | Bild-PDF | 4 sauber, 2 gedreht + unscharf |
| 5 | Verträge | PDF, Textebene | Rahmenvertrag Gerüstbau **30 Seiten**, Leasing, Lagermiete, 2 Arbeitsverträge |
| 4 | Notizen | TXT | Besprechungen, To-do, Telefonnotiz |
| 3 | Betriebs-Wiki | MD | Arbeitsanweisung Fassade, Lieferantenliste, Abnahme |
| 5 | Behörden | PDF, 2 davon Bild-PDF | Gewerbesteuer, Finanzamt, IHK, Berufsgenossenschaft (Scan), Kfz-Steuer (Scan) |
| 5 | Duplikate | bytegleiche Kopien | anderer Name, anderer Unterordner |
| 4 | sachfremd | 2 PDF, 1 TXT, 1 JPG | Router-Anleitung, Speisekarte, Kochrezept, Urlaubsfoto ohne Text |

Lieferanten und Nummernschemata: Farben Meister GmbH `FM-2025-00231`,
Gerüstbau Vogel & Sohn `GV 25/0067`, Werkzeughandel Brandt e.K. `R-25-1102`,
Autohof Westring GmbH (Tankkarte) `TK-2025-03-0091`, NeuKom Telekommunikation
GmbH `2025-7788-03`. Daten liegen über das ganze Jahr 2025.

## Bestand (Dateien 101–200, Erweiterung)

| Anzahl | Art | Format | Besonderheit |
|---|---|---|---|
| 35 | weitere Lieferantenrechnungen | 25 PDF Textebene, 10 Bild-PDF | dieselben 5 Lieferanten plus 3 neue; **Farben Meister jetzt 20 Rechnungen**, Tankkarte und Telefon lückenlos Januar–Dezember (12 Monate) |
| 20 | weitere Ausgangsrechnungen | PDF, Textebene | Nr. 2025-113 … 2025-132, 8 neue Kunden (2 Privat, WEG, Kita, Arztpraxis, 2 Gastronomie, Verein), mehrere Aufträge je Kunde, **4 Aufträge mit Teil- und Schlussrechnung** |
| 12 | weitere Angebote | DOCX | zu den neuen Aufträgen; A-2025-020 und A-2025-036 in je zwei Fassungen (Konflikt) |
| 10 | Kassenbelege | JPG Handyfoto | 6 sauber, 4 schief + unscharf; neuer Aussteller Getränkemarkt Quelle |
| 6 | Aufmaße / Stundenzettel | Bild-PDF | 4 sauber, 2 gedreht + unscharf; Aufmaß Ahornstraße 520 m² = Position der Schlussrechnung |
| 4 | Verträge | PDF, Textebene | Wartungsvertrag (Brandt), Betriebshaftpflicht-Police **12 Seiten**, Mobilfunkvertrag (NeuKom), Leasing 2 (NS-MH 251) |
| 4 | Notizen | TXT | Baustellen-Tagebücher Ahornstraße, Kita Regenbogen, Olivenbaum, TSV |
| 3 | Betriebs-Wiki | MD | Kundenliste (alle 20 Kunden), Preisliste 2025, Urlaubsplan |
| 3 | Behörden | PDF, 1 davon Bild-PDF | Handwerkskammer, Sondernutzung Gerüst (Ordnungsamt), Kfz-Zulassung (Scan) |
| 2 | weitere Korrekturrechnungen | PDF, Textebene | zu GV 25/0229 (Anfahrt laut § 5 Rahmenvertrag) und TB-25-118 (Konflikt) |
| 1 | Zahlungserinnerung | PDF, Textebene | `Rechnung (21).pdf`: Farben Meister mahnt FM-2025-00801 an — **gleicher Betrag, kein Konflikt**, aber Rechnungstext zum Verwechseln |

Neue Lieferanten: Tapeten & Boden Krüger GmbH `TB-25-118`, Containerdienst
Nordland GmbH `CN-2025-0801`, Arbeitsschutz Peters KG `AP20488`. Die neuen
Nummern der fünf alten Lieferanten fügen sich monoton in die bestehenden
Folgen ein (Nummer und Datum steigen gemeinsam, z. B. FM-2025-00689 vom 05.08.
→ 00712 vom 14.08. → 00760 vom 03.09.).

Keine weiteren Duplikate und keine weiteren sachfremden Dateien — die
Erweiterung zielt auf Ähnlichkeit, nicht auf Rauschen.

## Konflikte (Regel in `src/dokumentenassistent/konflikte.py`)

Gleiche Kategorie, gleicher Aussteller, Text nennt die Rechnungsnummer der
anderen Datei (oder gleiche Nummer), abweichender Betrag, anderes Datum →
Vorschlag „ersetzt". Der Altbetrag steht **nur** in der Erstfassung.

| A | B | Betrag A → B |
|---|---|---|
| `Rechnung (4).pdf` FM-2025-00231 | `Rechnung (9).pdf` Korrektur FM-2025-00298 „zu Rechnung Nr. FM-2025-00231" | 1.289,25 → 1.170,25 EUR |
| `Rechnung_Vogel.pdf` GV 25/0067 | `Rechnung (6).pdf` Korrektur GV 25/0081 | 4.998,00 → 3.998,40 EUR |
| `Rechnung (5).pdf` R-25-1102 | `Unbenannt.pdf` Korrektur R-25-1139 | 948,43 → 771,12 EUR |
| `Alt/Angebot_final.docx` A-2025-021 vom 12.06. | `Angebot_final_final2.docx` A-2025-021 vom 19.06. | 11.036,06 → 12.749,66 EUR |
| *ab Stufe 200:* `Alt/Angebot_Ahornstrasse.docx` A-2025-020 vom 05.05. | `Angebot_Ahornstrasse_neu.docx` A-2025-020 vom 16.05. (Fensterlaibungen ergänzt) | 24.127,25 → 26.326,37 EUR |
| `Alt/Angebot Turnraum.docx` A-2025-036 vom 15.09. | `Angebot Turnraum v2.docx` A-2025-036 vom 22.09. (Prallschutz ergänzt) | 1.175,72 → 1.708,84 EUR |
| `attachment (1).pdf` GV 25/0229 | `Rechnung (31).pdf` Korrektur GV 25/0240 „zu Rechnung Nr. GV 25/0229" | 1.850,45 → 1.749,30 EUR |
| `Rechnung (34).pdf` TB-25-118 | `Unbenannt (2).pdf` Korrektur TB-25-131 | 327,13 → 297,98 EUR |

Die Gerüst-Korrekturen begründen sich aus dem Rahmenvertrag: § 17 (vier Wochen
Standzeit im Grundpreis) bzw. § 5 (Anfahrt im Vertragsgebiet enthalten) —
Konflikt und Vertragsfrage hängen zusammen.

**Bewusst kein Konflikt:** die Zahlungserinnerung (`Rechnung (21).pdf`) nennt
FM-2025-00801 mit demselben Betrag 524,31 EUR wie `Rechnung (11).pdf`. Die
Schlussrechnungen ziehen ihre Teilrechnungen **nur mit Datum** ab („abzüglich
1. Teilrechnung vom 20.06.2025, bezahlt"), nicht mit Nummer — sonst würde die
Regel Teil- und Schlussrechnung als Konflikt vorschlagen.

## Duplikate

Zweiter Fundort in `sorted(rglob)`-Reihenfolge ist das Duplikat (so arbeitet
`werkstatt.erfassen`). Original → Kopie:

- `Downloads/Rechnung (4).pdf` → `Scans/Rechnung_Farben_Maerz.pdf` (Kopie einer Konfliktseite)
- `Alt/Rahmenvertrag_Geruestbau.pdf` → `Downloads/Vertrag.pdf` (30 Seiten doppelt)
- `Fotos Handy/IMG_2231.jpg` → `Scans/Beleg Baumarkt.jpg`
- `Downloads/2025-104.pdf` → `Scans/RE 2025-104 Kessler.pdf`
- `Alt/Scan_0099.pdf` → `Scans/Scan_0112.pdf` (Bild-PDF doppelt gescannt)

Unter den 200 Dateien teilen sich genau diese fünf Paare einen SHA-256; keine
zwei der neuen Dateien sind bytegleich (auch nicht die gleichlautenden
Telefonrechnungen — Nummer und Datum unterscheiden sie).

## Fragen (`golden.json` → `fragen`)

12 Fragen (Stufen 10–100) mit Sollstatus, Solldatei, Wortlaut und `ab_stufe`:
3 zu normalen Rechnungen (eine davon über den OCR-Pfad), 2 mit Konfliktbezug
(korrigierter Betrag), 2 zum Rahmenvertrag (Antwort **nur** auf Seite 17 bzw.
28), 1 zur Notiz (Betriebsurlaub), 1 zum Wiki (Tiefengrund zweimal), 3
`nicht_gefunden` (Bagger-Kaufvertrag, Dachdecker, Alarmanlage — die Wörter
kommen in keiner Datei vor).

8 weitere Fragen (Nr. 13–20, `ab_stufe: 200`):

| Nr. | Bezug | Frage | Soll |
|---|---|---|---|
| 13 | Verwechslung | Farben-Meister-Rechnung vom 14. August | `Rechnung (20).pdf`, 1.604,83 — unter 20 FM-Rechnungen, `Rechnung.pdf` ist vom 14.01. |
| 14 | Verwechslung | Rechnung an die Kita Regenbogen für den Turnraum | `Rechnung (27).pdf`, 1.708,84 — daneben Kita Sonnenschein und Regenbogen-Gruppenräume |
| 15 | Verwechslung | Telefonrechnung Oktober 2025 | `Telefon Oktober.pdf`, 192,93 — 12 fast gleichlautende NeuKom-Rechnungen |
| 16 | Aggregat | Gesamtsumme 2025 an Farben Meister | `pruefung: karte_datei_enthaelt` (siehe unten) |
| 17 | Aggregat | Gesamtsumme 2025 an die WEG Ahornstraße 3-5 | `pruefung: karte_datei_enthaelt` |
| 18 | Mahnung | Welche Nummer mahnt Farben Meister an | `Rechnung (21).pdf`, FM-2025-00801 — dieselbe Nummer steht in `Rechnung (11).pdf` |
| 19 | Teil-/Schlussrechnung | Restbetrag der WEG-Schlussrechnung | `Rechnung WEG.pdf`, 6.096,37 (26.326,37 − 10.710,00 − 9.520,00) |
| 20 | nicht gefunden | Photovoltaikanlage laut Angebot des Elektrikers | `nicht_gefunden` — beide Wörter kommen nirgends vor |

**`pruefung: "karte_datei_enthaelt"`** (Fragen 16, 17): Summenfragen kann das
Werkzeug nicht beantworten, ein Sollstatus `gefunden` wäre falsch. Deshalb
`status: null` (nicht gewertet) und stattdessen: Treffer, wenn die Datei der
**ersten** Belegkarte (`datei_ist`) in der Liste `dateien` der Frage steht —
für Frage 16 die 21 Farben-Meister-Rechnungsdateien (inkl. Korrektur und
Duplikat), für Frage 17 die vier WEG-Rechnungen. `lasttest_bericht.frage_zeile`
wertet dieses Feld noch nicht aus (offener Punkt); die Semantik steht in
`golden.json` → `pruefungen`.

## Stufen

`stufen`: `10`, `25`, `50`, `100`, `200` Dateien, kumulativ. Jede Stufe enthält
mindestens ein vollständiges Konfliktpaar, ein Duplikat **samt Original** und
eine OCR-unsichere Datei. Stufe 10 hat schon Rechnung + Korrektur + Kopie,
Stufe 25 bringt den 30-Seiten-Vertrag, Stufe 50 die Angebotsversionen, Stufe
200 die vollständige Erweiterung (Liste = Stufe 100 + die 100 neuen Pfade in
`sorted`-Reihenfolge).

## Gemessene Werte (Tesseract 5, `lang="deu"`, wie `auslesen.py` misst)

| Gruppe | Dateien | mittlere Wortkonfidenz |
|---|---|---|
| saubere Scans und Fotos (1–100) | 22 | **91,4 – 95,1** |
| unsichere Fotos (1–100) | `IMG_2240` 39,9 · `WhatsApp Image …` 38,9 · `IMG_2695` 42,1 · `IMG_3004` 30,8 | **30,8 – 42,1** |
| unsichere Scans (1–100) | `Scan_0113` 38,6 · `Scan_0114` 35,8 | |
| Urlaubsfoto `IMG_2650.jpg` | kein Wort erkannt | **0,0** |
| saubere Scans und Fotos (101–200) | 21 (`Scan_0118`–`0129`, `0131`, `0132`, `0134`, 6 JPG) | **87,5 – 95,2** (`Beleg Tankstelle Okt.jpg` 87,5, sonst ≥ 90,7) |
| unsichere Fotos (101–200) | `IMG_3199` 35,6 · `WhatsApp Image 2025-06-27 …` 45,2 · `IMG_3705` 36,7 · `IMG_3890` 45,7 | **35,6 – 45,7** |
| unsichere Scans (101–200) | `Alt/Scan_0130` 35,5 · `Scan_0133` 35,4 | |

Bei gleichen Verderb-Parametern schwankt Tesseract mit dem Text: zwei der
neuen Verderb-Kandidaten lieferten zunächst gar kein Wort (0,0); eine
zusätzliche Zeile (`IMG_3705`: „Vielen Dank") bzw. eine Giebel-Zeile
(`Scan_0130`) brachte sie in den Wortsalat-Bereich zurück.

Saubere Scans: 1600 × 2263 px, Arial 40 px, ungedreht. Saubere Fotos: 1,5°
gedreht, JPEG 92. Unsichere Fotos: 2,5° + `GaussianBlur(7.3)`, JPEG 85.
Unsichere Scans: 3° + `GaussianBlur(4.4)`. Die Schwelle ist scharf: ab etwa
5° Drehung findet Tesseract **gar kein** Wort mehr (Sicherheit 0,0), darunter
liefert es Wortsalat mit niedriger Konfidenz — das ist der interessantere
Fall, weil der Text dann *da* ist, aber nicht stimmt.

`pypdf` liefert für alle 35 Bild-PDFs keinen Text, der OCR-Pfad wird
erzwungen. `Scan_0099`: Nummer bewusst `FM-2025-00175`, weil Tesseract
`00160` als `00 160` trennt. Alle Sollwerte der neuen Bild-PDFs (Nummer,
Datum, Betrag, Aussteller) sind im OCR-Text der sauberen Scans wörtlich
bestätigt.

## Sollstatus-Verteilung

Dateien 1–100: 77 sicher · 8 konflikt · 7 ocr_unsicher · 5 duplikat · 3 unklar.
Dateien 101–200: 86 sicher · 8 konflikt · 6 ocr_unsicher.
Gesamt: 163 sicher · 16 konflikt · 13 ocr_unsicher · 5 duplikat · 3 unklar.

Das Urlaubsfoto zählt als `ocr_unsicher`, nicht `unklar`: `auslesen.py`
wertet „kein Wort erkannt" als Sicherheit 0,0 — ein leeres Ergebnis ist kein
sicheres Ergebnis. DOCX/TXT/MD tragen den Sollstatus, den sie mit Leseweg
bekommen sollen; ohne Leseweg meldet `auslesen.lies_seiten` sie als
`NichtLesbar` (→ unklar).

## Interne Stimmigkeit

Jede Rechnung: Netto = Σ Menge × Einzelpreis, USt = 19 % kaufmännisch
gerundet, Brutto = Netto + USt (`erzeugen.summen`). Ausgangsrechnung und
zugehöriges Angebot haben dieselben Positionen (z. B. Berger 6.287,96 EUR),
die Angebotsversion 2 ergänzt eine Position. Kassenbelege: Summe = Σ Zeilen.
Aufmaß Ringstraße 8 = 420 m² = Position der Ausgangsrechnung 2025-104.

Erweiterung: Schlussrechnung = Angebotssumme (Fassung 2), Teilrechnungen
werden brutto abgezogen, `restbetrag` in `golden.json` = Rechnungsbetrag −
Σ Teilrechnungen (WEG: 26.326,37 − 10.710,00 − 9.520,00 = 6.096,37; TSV:
6.644,96 − 3.570,00 = 3.074,96; Kita Regenbogen: 3.931,76 − 2.975,00 =
956,76; Olivenbaum: 7.192,36 − 4.760,00 = 2.432,36). Aufmaße Ahornstraße
520 m² / Kita Regenbogen 290 m² / Hauptstraße 12 210 m² = Positionen der
Schlussrechnungen; Preisliste-Wiki und Rechnungspositionen nennen dieselben
m²-Preise; Betriebsurlaub 28.07.–08.08. steht in Notiz, Urlaubsplan und
Bautagebuch, keine Baustelle arbeitet in dieser Zeit. Der Feiertag 03.10.
erscheint im Stundenzettel KW 40 und im Bautagebuch Olivenbaum.

Bekannte Unschärfe: die Ausgangsrechnungen 2025-113 … 2025-132 sind unter
sich datumsgeordnet, liegen aber zeitlich quer zu 2025-101 … 2025-112 (die
mit Datum bis Dezember eingefroren sind). Eine echte fortlaufende Vergabe wäre
nur mit Änderung der ersten 100 Dateien möglich gewesen.

## Abhängigkeiten

`reportlab`, `Pillow`, `python-docx`, Arial aus
`/System/Library/Fonts/Supplemental/Arial.ttf` (ohne Arial verfälscht die
Pillow-Standardschrift Umlaute und ß im OCR — dann stimmen die Scan-Sollwerte
nicht mehr). Prüfung: `pypdf`, `pytesseract` mit `deu`.
