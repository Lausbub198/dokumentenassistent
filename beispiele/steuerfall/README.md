# Beispielkorpus „Steuerfall 2025"

Synthetischer Eingangsordner für die Demo und für `pytest -m e2e`. Der Fall:
eine Privatperson (Andrea Beispiel, 12345 Neustadt) sammelt Unterlagen für die
Steuererklärung 2025 und vermietet zwei Wohnungen — **Wohnung Nord**
(Musterstraße 3) und **Wohnung Süd** (Gartenweg 12).

**Alles frei erfunden.** Keine echten Personen, Firmen, Adressen, Kontonummern
oder Steuer-IDs. Die enthaltene IBAN besteht aus Nullen und ist ungültig.

## Erzeugen

```bash
uv run python beispiele/steuerfall/erzeugen.py
```

Deterministisch: feste Texte, keine Zufallswerte, bytegleiche Ausgabe bei jedem
Lauf (reportlab `invariant=1`). Der Lauf überschreibt alle 13 Dateien in
`Quelle/`. Sollwerte je Datei: `tests/golden.json`.

## Die 13 Dateien und ihre Rolle

Die kryptischen Namen sind Absicht — der Assistent darf aus dem Dateinamen
nichts ableiten.

| Datei | Inhalt | Rolle in der Demo |
|---|---|---|
| `Rechnung (2).pdf` | Heizungsrechnung Nr. 2025-0815 vom 14.05.2025, Wohnung Nord, **1.240,00 EUR**, 2 Seiten, Textebene | Vorschlag mit Beleg; Konfliktseite A |
| `Rechnung (3).pdf` | Korrekturrechnung Nr. 2025-0815-K vom 02.06.2025 „zu Rechnung Nr. 2025-0815", **1.180,00 EUR**, Textebene | Konfliktseite B (`betrag`, Vorschlag „ersetzt") |
| `Scan_0043.pdf` | dieselbe Rechnung wie `Rechnung (2).pdf` als **Bild-PDF** ohne Textebene, sauber und gerade | OCR-Pfad, `per_ocr: true` |
| `Dokument1.pdf` | Mietvertrag Wohnung Nord, Kaltmiete **780,00 EUR**, Mietbeginn 01.03.2022, Mieter „Familie Beispiel", 2 Seiten, Textebene | Kategorie + Felder |
| `Dokument1 Kopie.pdf` | **bytegleiche** Kopie von `Dokument1.pdf` (gleicher SHA-256) | Duplikaterkennung |
| `Anhang.pdf` | Nebenkostenabrechnung Wohnung Süd 2024, Hausverwaltung Sommer & Partner, **1.912,40 EUR**, Textebene | zweite Kategorie |
| `IMG_8831.jpg` | Handyfoto einer Baumarktquittung („Hammer & Nagel", **17,90 EUR**), 12° schief und unscharf | „OCR unsicher" |
| `Scan_0044.pdf` | Grundsteuerbescheid Wohnung Süd 2025, Stadt Neustadt, **412,00 EUR**, Bild-PDF, sauber | zweiter OCR-Fall |
| `Lohnsteuer.pdf` | Lohnsteuerbescheinigung 2025, Muster Technik AG, Bruttoarbeitslohn **52.000,00 EUR**, Textebene | Kategorie Einkommen |
| `Beleg.pdf` | Spendenquittung Tierschutzverein Neustadt e.V., **250,00 EUR**, 12.11.2025, Textebene | Kategorie Sonstiges |
| `Versicherung_2025.pdf` | Beitragsrechnung Privathaftpflicht, Nordstern Versicherung, **89,50 EUR** jährlich, Textebene | Kategorie Versicherung |
| `Hausgeld.pdf` | Hausgeldabrechnung Wohnung Nord 2024, Immo Verwalt GmbH, **2.340,00 EUR**, Textebene | zweites Nord-Dokument |
| `Untitled.pdf` | Bedienungsanleitung WLAN-Router „NetBox 3000", 2 Seiten, kein Bezug zu Steuern oder Wohnungen | „unklar", keine passende Kategorie |

**Absichtlich nicht im Bestand: ein Kfz-Kaufvertrag.** Die Frage „Was steht im
Kaufvertrag für das Auto?" muss `nicht_gefunden` ergeben. In keiner Datei steht
„Kaufvertrag", „Fahrzeug", „Kfz" oder „Auto".

## Gemessene Werte (Tesseract 5.5.2, `lang="deu"`)

| Datei | Wörter | mittlere Wortkonfidenz |
|---|---|---|
| `Scan_0043.pdf` | 29 | **95,1** |
| `Scan_0044.pdf` | 30 | **94,3** |
| `IMG_8831.jpg` | 16 (Standard-PSM) / 14 (PSM 6) | **55,4** / **42,1** |

Die beiden Scans sind 1600 × 2263 px (A4-Verhältnis), Arial 44 px, schwarz auf
weiß, ungedreht — `2025-0815`, `1.240,00`, `412,00`, `Wohnung Nord` und
`Wohnung Süd` werden fehlerfrei erkannt. `pypdf` liefert für beide **keinen**
Text, der OCR-Pfad wird also erzwungen.

`IMG_8831.jpg` ist 12° gedreht und mit `GaussianBlur(4)` weichgezeichnet. Beide
Messungen liegen unter 60; bei stärkerer Unschärfe findet Tesseract mit dem
Standard-PSM überhaupt kein Wort mehr. Wer die Datei auswertet, muss also auch
den Fall „kein Wort erkannt" als *unsicher* behandeln, nicht als Fehler.

## Interne Stimmigkeit

Jede Summe geht auf, damit ein Konsistenzcheck nicht über den Korpus stolpert:

- Rechnung: 840,00 + 360,00 + 40,00 = **1.240,00**; Korrektur mit 300,00 Material = **1.180,00**
- Mietvertrag: 780,00 + 190,00 = 970,00; Kaution 2 × 780,00 = 1.560,00
- Nebenkosten: 980,50 + 412,30 + 198,60 + 321,00 = **1.912,40**; minus 1.800,00 Vorauszahlung = 112,40
- Hausgeld: 720,00 + 1.140,00 + 480,00 = **2.340,00** = 12 × 195,00
- Grundsteuer: 4 × 103,00 = **412,00**
- Quittung: 5,90 + 3,40 + 8,60 = **17,90**

Der Betrag `1.240,00` steht **nur** in `Rechnung (2).pdf` und `Scan_0043.pdf`,
nicht in der Korrekturrechnung — sonst wäre der Konflikt nicht eindeutig.

## Abhängigkeiten

`reportlab` (Textebene und Bild-PDF-Seite), `Pillow` (Scans und Foto) und die
Schrift `/System/Library/Fonts/Supplemental/Arial.ttf`. Fehlt Arial, fällt der
Generator auf die mitgelieferte Pillow-Schrift zurück — die verfälscht Umlaute
und `ß` im OCR („Süd" wird zu „SXd"), dann stimmen die Sollwerte der Scans
nicht mehr.
