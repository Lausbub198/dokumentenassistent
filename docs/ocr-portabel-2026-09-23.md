# Portable OCR-Engine: Messung und Entscheidung (23.09.2026)

> **Historisch, Stand 23.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


## Anlass: die Anforderung hat sich geändert

Die Messung vom 23.09.2026 (`docs/ocr-befund-2026-09-23.md`) hat Apple Vision empfohlen.
Der Auftraggeber verlangt jetzt eine Lösung, die auf **allen** Rechnern läuft. Damit fällt
Vision als Standard aus, obwohl es gemessen gewonnen hat. Vision bleibt in allen Tabellen
stehen — aber als **Messlatte** (was auf dieser Hardware erreichbar wäre), klar markiert als
**macOS-only**, nicht als Kandidat.

Die offene Frage lautete damit: **Ist Tesseract die beste portable Engine?** Das war
ungemessen. Diese Runde hängt drei portable Engines in denselben Messstand.

## Welche Engines es geworden sind — und warum

| Engine | Status | Begründung |
|---|---|---|
| `tesseract_vorverarbeitet` | gemessen | dieselbe Tesseract-Engine, davor `ocr_vorverarbeitung.vorverarbeite` (Graustufen → Kontrast → Entrauschen → Entzerren). Nur Pillow/numpy, keine externen Programme. |
| `paddleocr` | gemessen | eigene mehrsprachige Modelle (`lang="german"`), läuft auf CPU. |
| `easyocr` | gemessen | **Ersatz für surya** (siehe unten), deutsches Modell, CPU. |
| `surya` | **nicht gemessen** | Abhängigkeitskonflikt, nicht auflösbar ohne das Produkt zu ändern. |

### Warum surya ausfällt (Fehler wörtlich)

`surya-ocr` fordert in **jeder** geprüften Version (0.14.7 bis 0.22.1) `pillow<11`. Das Produkt
fordert `pillow>=11.0` und hat 12.3.0 installiert. Der Resolver:

```
× No solution found when resolving dependencies:
╰─▶ Because all versions of surya-ocr depend on pillow>=10.2.0,<11.0.0
    and you require surya-ocr, we can conclude that you require
    pillow>=10.2.0,<11.0.0.
    And because you require pillow>=11.0, we can conclude that your
    requirements are unsatisfiable.
```

Das ist kein Installationsproblem, das sich mit Zeit lösen ließe: surya hier aufzunehmen
hieße, Pillow im **Produkt** zurückzustufen, um eine Engine zu *messen*. Das wäre die
Reihenfolge verkehrt herum. Also übersprungen und, wie beauftragt, `easyocr` genommen
(`python-doctr` wäre ebenfalls gegangen — es löst gegen `pillow>=11` sauber auf —, aber
easyocr bringt ein ausgewiesen deutsches Modell mit, doctr englisch/französisch trainierte
Standardmodelle).

Jede Engine ist eine eigene optionale Abhängigkeitsgruppe (`ocr`, `ocr-paddle`, `ocr-easy`).
Fehlt eine Gruppe, überspringt `pruefe_engines` die Engine **mit Meldung auf stderr** — kein
stiller Verzicht, und der Lauf bricht nicht ab.

## Messstand

Wahrheitslauf gegen die eingebettete Textebene, identische Bedingungen zum 23.09.:
Korpus unverändert, `--seiten 150`, Seed 42, 300 dpi, `min_zeichen` 200.
`tesseract`, `vision` und `vision_korrektur` wurden **nicht neu gemessen**, sondern über
`--uebernehmen` aus `beweise/ocr-reihenfolge/2026-09-23/laeufe.jsonl` mitgeführt (432 Zeilen,
0 fehlend). Belege: `beweise/ocr-portabel/2026-09-23/` (`laeufe.jsonl`, `bericht.md`).

**Ausgewertet werden 96 Seiten, nicht 150.** Zwei Gründe, beide benannt statt geglättet:

1. Der Lauf wurde nach 100 gemessenen Seiten je neuer Engine abgebrochen, weil die Maschine
   für andere Arbeit gebraucht wurde (Videoschnitt, loadavg zeitweise > 40). Die bereits
   geschriebenen Zeilen bleiben gültig — das Protokoll wird zeilenweise geschrieben und sofort
   geflusht, genau dafür.
2. Ausgewertet wird nur die **Schnittmenge**, die jede der sechs Engines gemessen hat, und je
   Engine und Seite genau eine Zeile. Sonst stünden Mediane über verschiedene Seitenmengen
   nebeneinander. Von den 100 Messungen bleiben 96 Seiten: der Korpus enthält gleichnamige
   Dateien in verschiedenen Ordnern, und das Protokoll führt nur den Dateinamen.

Eine Seite wiegt damit gut **1 %**. Unterschiede unter etwa 4 Prozentpunkten bei den Zählungen
sind Rauschen; die Entscheidung unten steht auf Abständen, die deutlich darüber liegen.

## Ergebnistabelle

**Alle 96 Seiten** (Zahlentreue = gefundene von genannten Zahlen; „erfunden" = Nennungen im
OCR-Text, die die Referenz nicht führt)

| Engine | portabel | F1 Wort | F1 Trigramm | CER Median | Zahlentreue | Zahlen erfunden | OCR s/Seite |
|---|---|---|---|---|---|---|---|
| `tesseract` (heutiges Produkt) | ja | 0.9642 | 0.9803 | 0.0664 | 84.3 % (1690/2004) | **140** | 0.98 |
| `tesseract_vorverarbeitet` | ja | 0.9600 | 0.9784 | **0.0558** | 82.6 % (1656/2004) | 168 | 1.48 |
| **`paddleocr`** | **ja** | **0.9808** | **0.9831** | 0.0513 | **94.7 % (1897/2004)** | 222 | 29.35 |
| `easyocr` | ja | 0.9087 | 0.9615 | 0.0722 | 84.6 % (1695/2004) | 413 | 10.38 |
| `vision` *(Messlatte, macOS-only)* | **nein** | 0.9647 | 0.9786 | 0.1166 | 91.4 % (1831/2004) | 148 | 0.22 |
| `vision_korrektur` *(Messlatte, macOS-only)* | **nein** | 0.9718 | 0.9791 | 0.1133 | 91.0 % (1823/2004) | 142 | 0.35 |

**Tragfähige Teilmenge** — die 58 Seiten, auf denen *jede* Engine eine CER ≤ 0,3 erreicht.
Der Rest ist kein Lesequalitäts-, sondern ein Reihenfolgeproblem (Befund vom 23.09.: die
Textebene liest mehrspaltige Seiten und Tabellen in anderer Folge als eine OCR, die dem Bild
folgt).

| Engine | F1 Wort | F1 Trigramm | CER Median | Zahlentreue | Zahlen erfunden |
|---|---|---|---|---|---|
| `tesseract` | 0.9747 | 0.9877 | 0.0144 | 91.8 % (961/1047) | 58 |
| `tesseract_vorverarbeitet` | 0.9739 | 0.9872 | 0.0166 | 91.9 % (962/1047) | 51 |
| **`paddleocr`** | **0.9823** | **0.9920** | **0.0123** | **93.8 % (982/1047)** | **39** |
| `easyocr` | 0.9192 | 0.9654 | 0.0222 | 86.1 % (901/1047) | 147 |
| `vision` *(Messlatte)* | 0.9776 | 0.9881 | 0.0161 | 91.2 % (955/1047) | 29 |
| `vision_korrektur` *(Messlatte)* | 0.9774 | 0.9876 | 0.0161 | 90.7 % (950/1047) | 28 |

## Paarweise je Seite gegen `tesseract`

Der Median hat am 23.09. eine Rangfolge behauptet, die der Einzelvergleich nicht hergab.
Deshalb wieder Seite gegen Seite — alle Engines lesen dieselben 96 Seiten. Δ ist als Gewinn
der neuen Engine orientiert (bei CER umgedreht: weniger ist besser).

| Engine | Kennzahl | Δ Median | Δ Mittel | besser | gleich | schlechter |
|---|---|---|---|---|---|---|
| `tesseract_vorverarbeitet` | F1 Wort | −0.0013 | −0.0060 | 25 | 20 | **51** |
| `tesseract_vorverarbeitet` | F1 Trigramm | −0.0004 | −0.0037 | 36 | 8 | **52** |
| `tesseract_vorverarbeitet` | CER | −0.0003 | +0.0022 | 32 | 13 | **51** |
| **`paddleocr`** | **F1 Wort** | **+0.0120** | **+0.0382** | **81** | 1 | 14 |
| **`paddleocr`** | **F1 Trigramm** | **+0.0043** | **+0.0271** | **82** | 0 | 14 |
| `paddleocr` | CER | +0.0019 | +0.0220 | 63 | 3 | 30 |
| `easyocr` | F1 Wort | −0.0453 | −0.0321 | 16 | 1 | **79** |
| `easyocr` | F1 Trigramm | −0.0194 | −0.0025 | 20 | 0 | **76** |
| `easyocr` | CER | −0.0074 | +0.0178 | 26 | 1 | **69** |
| `vision` *(Messlatte)* | F1 Wort | +0.0046 | +0.0200 | 65 | 1 | 30 |
| `vision` *(Messlatte)* | F1 Trigramm | +0.0010 | +0.0165 | 53 | 1 | 42 |
| `vision` *(Messlatte)* | CER | ±0.0000 | −0.0210 | 47 | 2 | 47 |

Der Befund ist diesmal nicht knapp: `paddleocr` liest auf **81 von 96** Seiten mehr richtige
Wörter als Tesseract und auf **82 von 96** mehr richtige Trigramme. Zum Vergleich — Vision,
die Messlatte, schafft 65 bzw. 53. Die portable Engine schlägt hier die macOS-Engine.

## Zahlen und Fristen

Über alle 96 Seiten summiert:

| Engine | Zahlen + Daten verfehlt | Zahlen erfunden | davon auf den 38 Seiten ohne tragfähige Referenz |
|---|---|---|---|
| `tesseract` | 320 | 140 | 82 |
| `tesseract_vorverarbeitet` | 352 | 168 | 117 |
| **`paddleocr`** | **110** | 222 | 183 |
| `easyocr` | 323 | 413 | 266 |
| `vision` *(Messlatte)* | 176 | 148 | 119 |

`paddleocr` verfehlt **110 statt 320** Zahlen und Fristen (−66 %) — deutlicher, als Vision es
schafft (176). Der einzige Wert, der schlechter aussieht, ist `zahlen_erfunden` (222 gegen 140).
Der Einzelvergleich zeigt, dass das **kein Erfindungsproblem** ist:

| Vergleich gegen `tesseract`, je Seite | weniger erfunden | gleich | mehr erfunden |
|---|---|---|---|
| `paddleocr` | **45** | 40 | 11 |
| `easyocr` | 30 | 40 | 26 |
| `tesseract_vorverarbeitet` | 16 | 58 | 22 |

Auf **45 von 96** Seiten erfindet `paddleocr` *weniger* als Tesseract, auf 11 mehr. Die Summe
kippt über wenige Extremseiten: 183 der 222 Nennungen fallen auf die 38 Seiten, auf denen die
Referenz selbst nicht trägt (Tabellen, Stempel, Kopfzeilen, die die Textebene nicht führt) —
auf einer einzigen Seite allein 82. Auf der tragfähigen Teilmenge steht `paddleocr` mit **39
gegen 58** *besser* als Tesseract. `zahlen_erfunden` ist hier also, wie im Modul-Docstring
festgehalten, kein Halluzinationszähler, sondern zum guten Teil ein Maß dafür, dass eine
Engine **mehr** liest, als in der Textebene steht.

## Laufzeit (Information, kein Ausschlusskriterium)

OCR-pflichtig sind nicht alle Seiten des Bestands, sondern die ohne Textebene: **134 Seiten**
(34 PDFs mit 119 Seiten plus 15 Bilddateien). Hochgerechnet auf einen vollständigen
Einlesevorgang, gemessen an den ersten 40 Seiten des Laufs — **vor** der Fremdlast:

| Engine | s/Seite (Median) | 134 Seiten |
|---|---|---|
| `vision` *(Messlatte)* | 0.22 | 0,5 min |
| `tesseract` | 0.98 | 2,2 min |
| `tesseract_vorverarbeitet` | 1.48 | 3,3 min |
| `easyocr` | 10.38 | 23 min |
| **`paddleocr`** | **29.35** | **66 min** |

Eine Stunde einmalig beim Einlesen ist vertretbar; das Einordnen mit dem Sprachmodell dauert
ohnehin länger. **Wichtig für die Bewertung dieser Spalte:** die letzten 10 der 100 gemessenen
Seiten liefen unter Fremdlast und sind unbrauchbar (`paddleocr` Median 30 s → 57 s, `easyocr`
12 s → 24 s). Die Tabelle oben nutzt deshalb ausschließlich die ersten 40 Seiten; der Median
über alle 96 läge bei 31.1 s (`paddleocr`) bzw. 11.9 s (`easyocr`) und wäre eine Aussage über
die Maschinenlast, nicht über die Engine.

**Nicht gemessen:** die beauftragte Laufzeitprobe über 10 Seiten aus PDFs **ohne** Textebene.
Sie war als zweiter Schritt eingeplant und ist der Fremdlast zum Opfer gefallen — jede Zahl
daraus wäre Maschinenlast gewesen. Das Kommando steht im Modul-Docstring; nachzuholen, sobald
die Maschine frei ist. Insbesondere die Frage „kommt überhaupt Text heraus" ist für
`paddleocr` und `easyocr` damit **offen**.

## Entscheidung: **`paddleocr`**

Regel, unverändert seit dem 23.09.: empfohlen wird die portable Engine, die gegenüber
`tesseract` **F1 Wort und F1 Trigramm hält oder verbessert** und die **Zahlentreue nicht
verschlechtert**.

1. **F1 Wort** — besser: 0.9808 gegen 0.9642, paarweise 81:14. ✔
2. **F1 Trigramm** — besser: 0.9831 gegen 0.9803, paarweise 82:14. ✔
3. **Zahlentreue** — deutlich besser: 94.7 % statt 84.3 %, 110 statt 320 verfehlte Zahlen und
   Fristen. ✔
4. **`zahlen_erfunden`** — in der Summe höher (222 gegen 140), paarweise aber auf 45 von 96
   Seiten *niedriger* und auf der tragfähigen Teilmenge mit 39 gegen 58 klar besser. Kein
   Ausschluss, aber die Stelle, die bei einer Nachmessung als erste zu prüfen ist. ⚠
5. **Laufzeit** — 66 min für einen vollen Einlesevorgang, gegen 2,2 min heute. Nebenbedingung,
   kein K.-o.

Die beiden anderen fallen durch:

* **`tesseract_vorverarbeitet`** verschlechtert beides (paarweise 25:51 bei F1 Wort, 36:52 bei
  F1 Trigramm) und verfehlt mehr Zahlen (352 statt 320). Bemerkenswert: die **CER sinkt**
  (0.0558 gegen 0.0664) — genau die Kennzahl, die am 23.09. als irreführend entlarvt wurde.
  Hätte diese Runde wieder nach CER entschieden, wäre die Vorverarbeitung die Empfehlung
  gewesen. Sie ist es nicht.
* **`easyocr`** ist auf diesem Korpus deutlich schwächer (paarweise 16:79 bei F1 Wort) und
  erfindet am meisten (413).

## Was ein Wechsel im Produkt bedeutet (benannt, **nicht** umgebaut)

`auslesen.py` ist in dieser Runde nicht angefasst worden. Die konkreten Stellen:

1. **Konfidenz: ja, `paddleocr` liefert eine.** Das Ergebnis von `predict` führt neben
   `rec_texts` ein Feld `rec_scores` — ein Wert in 0…1 je erkanntem Textstück. Ein Äquivalent
   zu `conf/100` aus `pytesseract.image_to_data` existiert also.
2. **Granularität ist eine andere.** `auslesen._wortkonfidenzen` bekommt von Tesseract eine
   Konfidenz je **Wortkasten** und mittelt darüber (`auslesen.py:146`). `rec_scores` hängt an
   der erkannten **Textzeile**. PaddleOCR kennt eine Option `return_word_box`; ob sie das
   deutsche Modell in Wortkästen zerlegt, ist **ungeprüft**.
3. **Die Schwelle 0,6 muss neu abgeleitet werden.** `werkstatt.py:52` (`ocr_schwelle = 0.6`)
   entscheidet über den Status `ocr_unsicher`, und der entscheidet, ob eine Datei überhaupt ans
   Modell geht (`werkstatt.py:192`, `:223`). Die 0,6 stammen aus gemessenen Tesseract-Werten.
   Die Verteilungen sind nicht dieselbe Größe: auf **einem** synthetischen Testbild (nur zur
   Veranschaulichung, keine Fixture-Messung) liefert Tesseract im Mittel 0.679 und läge damit
   *über* der Schwelle, PaddleOCR 0.999. Line-Scores liegen sichtbar höher und näher an 1 —
   eine Schwelle von 0,6 würde unter PaddleOCR praktisch nie greifen und den Schutz
   `ocr_unsicher` faktisch abschalten. Die Ableitung an denselben Fixtures zu wiederholen ist
   **Pflicht**, nicht Kür.
4. **Regel „leeres Ergebnis ist kein sicheres Ergebnis" bleibt nötig.** Die Abbildung „keine
   Erkennung → Sicherheit 0.0" muss mitwandern. Wie oft `paddleocr` auf echten Scans gar
   nichts liefert, ist mangels Laufzeitprobe **ungemessen**.
5. **Absatz- und Tabellenstruktur ist ungeprüft.** `fundstellen.zerlege` erwartet die Struktur,
   die `auslesen` aus dem Text herstellt. Ob aneinandergehängte PaddleOCR-Zeilen dieselbe
   Absatztrennung tragen, hat diese Messung nicht betrachtet — sie hat Zeichen, Wörter und
   Zahlen verglichen, und die Leitkennzahl ignoriert Reihenfolge ausdrücklich.
6. **Gewicht der Abhängigkeit.** `paddlepaddle` + `paddlex` ziehen ein vollständiges
   Inferenz-Framework nach (u. a. `opencv-contrib-python`, `shapely`, `pandas`, `protobuf`) und
   laden die Modelle beim ersten Lauf aus dem Netz nach `~/.paddlex`. Heute hängt der
   Auslese-Pfad an einem `tesseract`-Binary. Für ein Produkt, das „auf allen Rechnern läuft"
   heißen soll, ist das die eigentliche Frage an diesen Wechsel — sie ist eine
   Betriebsentscheidung, keine Messfrage, und hier nur benannt.
7. **Erstaufruf kostet extra.** Das Laden der Modelle schlägt einmalig mit rund 5 s zu Buche
   (erste Seite 25 s gegen 21 s im eingeschwungenen Zustand, separat gemessen).

## Grenzen

* **Der Wahrheitslauf misst auf den falschen Seiten für den Betriebsfall.** Gemessen wird auf
  Seiten **mit** Textebene, weil es nur dort eine Referenz gibt: sauber gerenderte PDF-Seiten
  bei 300 dpi. Im Betrieb geht es um die **134 Seiten ohne** Textebene — echte Scans und Fotos,
  schief, verrauscht, wechselnd belichtet. Gerade die Vorverarbeitung könnte dort mehr bringen
  als auf sauberen Renderings; ihr schlechtes Abschneiden hier ist **kein** Beleg dafür, dass
  sie auf Scans nichts nützt. Die ganze Messung ist ein **Hinweis, kein Beweis** für den
  Betriebsfall. Zehn handgeprüfte echte Scan-Seiten wären dafür aussagekräftiger als 96
  gerenderte.
* 96 statt 150 Seiten; eine Seite wiegt 1 %. Die Entscheidung steht auf 81:14 und 82:14 —
  Abstände, die eine einzelne Seite nicht dreht.
* Die Vorverarbeitung wurde nur **als Ganzes** gemessen. Welche der vier Stufen (Graustufen,
  Kontrast, Entrauschen, Entzerren) den Rückschritt verursacht, ist offen; jede Stufe ist
  einzeln abschaltbar, gemessen wurde das nicht.
* `paddleocr` lief mit abgeschalteten Vorstufen (Seitenorientierung, Entzerrung,
  Zeilenorientierung), damit der Vergleich die Erkennung misst und nicht ungleiche Vorstufen.
  Auf schiefen Scans könnten genau diese Vorstufen den Unterschied machen — ungemessen.
* Der Vergleich der Engines untereinander ist gültig (alle lesen dieselben Seiten gegen
  dieselbe Referenz); die absoluten CER-Werte bleiben eine Obergrenze, kein Fehleranteil.

## Offen

* Laufzeitprobe auf PDFs ohne Textebene (10 Seiten) — nicht gemessen, Maschinenlast.
* Die 50 fehlenden Seiten des Wahrheitslaufs (96 von 150) — nachzuholen mit `--fortsetzen`,
  das Protokoll überspringt die bereits gemessenen Kombinationen.
* Punkte 1–7 des Abschnitts „Was ein Wechsel im Produkt bedeutet" sind **geplant, nicht
  gemessen**.
* `python-doctr` wurde nicht gemessen (höchstens drei neue Engines); es löst gegen `pillow>=11`
  sauber auf und wäre der nächste Kandidat, falls `paddleocr` am Abhängigkeitsgewicht scheitert.
