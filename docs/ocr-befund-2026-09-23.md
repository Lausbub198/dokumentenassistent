# OCR-Engine: Entscheidung nach reparierter Leitkennzahl (23.09.2026)

> **Historisch, Stand 23.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


> ## ÜBERHOLT — die hier getroffene Entscheidung gilt nicht mehr
>
> Dieses Dokument endet mit „**Entscheidung: wechseln auf Apple Vision**". Das war am 23.09.
> richtig gemessen und ist seither **dreifach** überholt worden. Wer die Reihe von vorn liest,
> darf nicht bei dieser Seite stehenbleiben:
>
> 1. **`docs/ocr-portabel-2026-09-23.md`** — Apple Vision läuft nur auf macOS. Der Auftraggeber
>    hat ausdrücklich etwas verlangt, „das auf allen PC einigermaßen funktioniert". Ergebnis:
>    **PaddleOCR**.
> 2. **`docs/ocr-scans-2026-09-23.md`** — Gegenlese-Runde auf 10 echten Scans, menschliches
>    Urteil des Auftraggebers.
> 3. **Drehungsmessung 24.09.** (`dcfc336`) — nur `use_doc_orientation_classify` hilft; der
>    Sammelschalter wäre *schlechter* als gar keine Drehung gewesen (168 gegen 179 erkannte
>    Zahlen).
>
> **Was heute gilt, steht in `modelle.yaml`:** `ocr: paddleocr`, `ocr_drehung: true`.
> Eingebaut mit `c9a69dc`. Vermerk nachgetragen am 24.09.2026 (offener Punkt 18).

## Was repariert wurde

Der Lauf vom 23.09. hat mit CER (Editierdistanz je Zeichen) entschieden. Diese Kennzahl war
für diese Frage **falsch gewählt** — nicht ungenau, sondern an der falschen Größe gemessen:

> Auf **51 von 144** Seiten lag die CER bei *allen drei* Engines zugleich über 0,3, obwohl die
> OCR gleich viel Text liefert wie die Referenz (Median-Verhältnis Zeichen OCR/Referenz 1,0).
> Es fehlt nichts. Die **Lesereihenfolge** unterscheidet sich — mehrspaltige Seiten, Tabellen,
> Kopf-/Fußzeilen. Die Editierdistanz zählt jede Umstellung als Lesefehler.

Auf rund einem Drittel der Stichprobe hat die Leitkennzahl damit Layout gemessen, nicht
Lesequalität. Die Entscheidung „kein Wechsel" stand auf genau dieser Kennzahl.

Neu hinzugekommen (die alten Kennzahlen bleiben vollständig erhalten):

* `wortmengen_kennzahlen` — Präzision, Ausbeute, F1 über die Wort-**Multimengen**. Ein Wort,
  das dreimal auf dem Papier steht, muss dreimal gelesen werden; eine Menge (statt Multimenge)
  würde `900 900 900` und `900` gleich bewerten und damit genau die Wiederholung verschlucken,
  auf die es bei Beträgen in Tabellen ankommt.
* `zeichen_ngramm_kennzahlen` — dasselbe über Zeichen-Trigramme. Fängt Teilwortfehler, die die
  Wortmenge komplett verwirft: `Rechnung` gegen `Rechnunq` ist dort ein Totalausfall (F1 0),
  über Trigramme bleiben sechs von acht Grammen stehen.

Beide nutzen dieselbe `normalisiere` wie CER/WER — dieselbe Funktion, kein Herkunftswissen,
keine Engine bevorzugt. Beide sind reihenfolge-unabhängig: dieselben Wörter in anderer Folge
ergeben F1 1,0, während die CER hoch bleibt (so getestet).

## Warum neu gemessen wurde (und warum das trotzdem derselbe Vergleich ist)

`beweise/ocr/2026-09-23/laeufe.jsonl` enthält **keinen OCR-Text** — geprüft über alle 488
Zeilen: pro Seite stehen dort nur `cer`, `wer`, `zeichen_ocr` und die Zahlentreue-Zähler. Ein
Nachrechnen der neuen Kennzahlen aus den vorhandenen Läufen ist deshalb unmöglich; es wurde
neu gemessen, mit **identischen Messbedingungen** (Seed 42, 150 Seiten, 300 dpi, `min_zeichen`
200, dieselben drei Engines, derselbe Korpus). Der OCR-Text lag dabei nur im Speicher; in
`laeufe.jsonl` und Bericht steht weiterhin kein Dokumentinhalt.

Dass es dieselbe Stichprobe ist, muss man nicht glauben — die alten Kennzahlen reproduzieren
**Stelle für Stelle**: CER-Median 0.0599 / 0.1013 / 0.0998, Zahlentreue 2729 / 2995 / 2976 von
3265, Datumstreue 196 / 198 / 198 von 204, identisch zum Lauf von 17:41 Uhr. Abweichungen gibt
es nur in der Laufzeit (Maschinenlast), nicht in einer einzigen Lesekennzahl.

Neuer Lauf: `beweise/ocr-reihenfolge/2026-09-23/` (`laeufe.jsonl`, `bericht.md`). Der alte
Ordner bleibt unverändert.

## Alt und neu nebeneinander

**Alle Seiten (150 je Engine)**

| Engine | F1 Wort | F1 Trigramm | CER Median | Zahlentreue | Zahlen erfunden | OCR s/Seite |
|---|---|---|---|---|---|---|
| tesseract (heutiges Produkt) | 0.9647 | **0.9808** | **0.0599** | 83.6 % (2729/3265) | 230 | 1.04 |
| vision | 0.9720 | 0.9793 | 0.1013 | **91.7 % (2995/3265)** | 196 | **0.22** |
| vision_korrektur | **0.9727** | 0.9810 | 0.0998 | 91.1 % (2976/3265) | **187** | 0.35 |

**Tragfähige Teilmenge — alle Engines CER ≤ 0,3 (97 von 150 Messungen je Engine)**

| Engine | F1 Wort | F1 Trigramm | CER Median | Zahlentreue | Zahlen erfunden | OCR s/Seite |
|---|---|---|---|---|---|---|
| tesseract | 0.9728 | 0.9877 | **0.0153** | 90.8 % (1676/1845) | 123 | 1.29 |
| vision | **0.9794** | **0.9883** | 0.0198 | **92.4 % (1705/1845)** | 50 | **0.27** |
| vision_korrektur | 0.9782 | 0.9875 | 0.0200 | 91.6 % (1690/1845) | **48** | 0.40 |

Die Teilmenge ist der Rest, auf dem die alte Kennzahl überhaupt trug: 53 der 150 Messungen
fallen heraus, weil dort **alle** Engines zugleich über 0,3 liegen. Sichtbar wird, dass CER
dort auf ein Sechstel fällt (0.0599 → 0.0153), während die F1-Werte sich kaum bewegen
(0.9647 → 0.9728). Genau das ist der Beweis, dass die ausgeschlossenen Seiten kein
Lesequalitäts-, sondern ein Reihenfolgeproblem waren.

## Der entscheidende Blick: Seite gegen Seite, nicht Median gegen Median

Die Median-Abstände oben liegen in der dritten Nachkommastelle und tragen keine Entscheidung.
Da alle Engines dieselben Seiten lesen, ist der **paarweise** Vergleich je Seite die richtige
Form (Δ = Vision − Tesseract; bei F1 ist mehr besser, bei CER weniger):

| Kennzahl | Δ Median | Δ Mittel | besser | gleich | schlechter |
|---|---|---|---|---|---|
| F1 Wort (vision) | +0.0052 | +0.0180 | **105** | 2 | 43 |
| F1 Trigramm (vision) | +0.0013 | +0.0160 | **89** | 1 | 60 |
| CER (vision) | ±0.0000 | +0.0262 | 73 | 3 | **74** |
| F1 Wort (vision_korrektur) | +0.0078 | +0.0201 | **106** | 2 | 42 |
| F1 Trigramm (vision_korrektur) | +0.0010 | +0.0171 | **97** | 1 | 52 |
| CER (vision_korrektur) | ±0.0000 | +0.0264 | 72 | 8 | 70 |

Das ist der eigentliche Befund: **paarweise ist die CER ein Münzwurf** (73 zu 74), während der
Median-Vergleich 0.0599 gegen 0.1013 einen klaren Vorsprung für Tesseract behauptet hat. Der
Vorsprung stammt aus der Höhe einzelner Ausreißer, nicht aus mehr richtig gelesenen Seiten —
und die Ausreißer sind genau die umsortierten Layoutseiten. Reihenfolge-unabhängig gemessen
liest Vision auf **105 von 150** Seiten mehr richtige Wörter.

Zahlen und Fristen, über alle 150 Seiten summiert:

| Engine | Zahlen + Daten verfehlt | Zahlen erfunden |
|---|---|---|
| tesseract | 544 | 230 |
| vision | **276** | 196 |
| vision_korrektur | 295 | **187** |

## Entscheidung: **wechseln** auf Apple Vision, `usesLanguageCorrection` aus

Die Regel (vor der Messung festgelegt, nur die Leitkennzahl repariert): empfohlen wird die
Engine, die **F1 Wort und F1 Trigramm hält oder verbessert** und die **Zahlentreue nicht
verschlechtert**; `zahlen_erfunden` bleibt Ausschlusskriterium.

`vision` erfüllt alles:

1. **F1 Wort** — besser, paarweise auf 105 von 150 Seiten (Δ Median +0.0052). ✔
2. **F1 Trigramm** — besser, paarweise auf 89 von 150 Seiten (Δ Median +0.0013). Im
   unpaarweisen Median über alle Seiten liegt Vision mit 0.9793 gegen 0.9808 um 0.0015
   darunter, auf der tragfähigen Teilmenge mit 0.9883 gegen 0.9877 darüber — beides innerhalb
   des Rauschens. Als „gehalten" gewertet, paarweise als „verbessert". ✔
3. **Zahlentreue** — deutlich besser: 276 statt 544 verfehlte Zahlen und Daten (−49 %),
   Zahlentreue 91.7 % statt 83.6 %. ✔
4. **`zahlen_erfunden`** — 196 statt 230, also *niedriger*; kein Ausschluss. ✔

Dazu kommt die Laufzeit: 0.22 s statt 1.04 s je Seite, Faktor 4,7.

Warum **nicht** `vision_korrektur`, obwohl es beim F1 Wort minimal vorn liegt: die
Sprachkorrektur repariert Text anhand eines Sprachmodells und ist genau der Mechanismus, der
Zahlen und Namen erfinden kann. Ihr Vorsprung ist mit +0.0007 beim F1 Wort gegenüber `vision`
nicht messbar von Null verschieden, ihre Zahlentreue ist schlechter (295 statt 276 verfehlt),
und sie kostet 60 % mehr Laufzeit. Für einen Assistenten mit Zitatpflicht ist die Variante
ohne Sprachmodell die konservative — und hier auch die bessere.

**Was sich gegenüber dem 23.09. ändert:** die Empfehlung kippt von „kein Wechsel" auf
„wechseln". Nicht, weil neue Zahlen gemessen wurden — die alten sind Stelle für Stelle
dieselben —, sondern weil der einzige Grund gegen Vision (CER 0.1013 gegen 0.0599) paarweise
nicht existiert und reihenfolge-unabhängig verschwindet.

### CER und WER bleiben, aber als Nebenkennzahl

Sie lösen Zeichenfehler *innerhalb* einer Zeile feiner auf als F1 über Multimengen und zeigen
Verwechslungen (`Miete`/`Mlete`), die eine Trigramm-Überlappung teilweise übersieht. Sie können
hier aber nicht die Leitkennzahl sein, weil sie Position mitmessen und die Referenz (die
eingebettete Textebene) eine andere Leserichtung hat als eine OCR, die dem Bild folgt. Ihre
absoluten Werte sind eine **Obergrenze** des Fehleranteils, kein Fehleranteil.

## Was ein Wechsel im Produkt bedeuten würde (benannt, nicht umgebaut)

`auslesen.py` ist in dieser Runde **nicht** angefasst worden. Der Weg dorthin ist aber kein
Einzeiler, und das sind die konkreten Stellen:

1. **Wortkästen.** `auslesen._wortkonfidenzen` ruft
   `pytesseract.image_to_data(..., output_type=DICT)` und bekommt je **Wortkasten** eine
   Konfidenz. Vision liefert `VNRecognizedTextObservation` je **Textblock/Zeile**; einzelne
   Wortkästen gibt es nur indirekt über `boundingBoxForRange:error:` auf dem
   `VNRecognizedText`. Ein Wechsel ändert also die Granularität der Kästen, nicht nur den
   Anbieter.
2. **Konfidenz-Äquivalent: ja, aber andere Bezugsgröße.** `VNRecognizedText.confidence` ist
   0…1 und damit formal das Gegenstück zu `conf/100`. Es ist jedoch die Konfidenz eines
   *Kandidaten für einen Textblock*, nicht der Mittelwert über Wortkästen. Die Verteilung ist
   damit eine andere.
3. **Der Schwellenwert 0,6 müsste neu abgeleitet werden.** `werkstatt.py:52`
   (`ocr_schwelle: float = 0.6`) entscheidet über den Status `ocr_unsicher`, und dieser Status
   entscheidet, ob eine Datei überhaupt ans Modell geht (`werkstatt.py:192`, `:223`). Die 0,6
   stammen aus gemessenen Tesseract-Werten (sauberer Scan 0.958, unscharfes Bild 0.0). Diese
   Messung müsste mit Vision an denselben Fixtures wiederholt werden; die Zahl ungeprüft zu
   übernehmen wäre genau die Sorte Annahme, die dieser Befund gerade korrigiert hat.
4. **Regel „leeres Ergebnis ist kein sicheres Ergebnis" bleibt nötig.** In der Laufzeitprobe
   liefert Vision auf 2 von 10 Seiten ohne Textebene gar keinen Text (Tesseract: 1). Die
   Abbildung „keine Erkennung → Sicherheit 0.0" muss also mitwandern.
5. **Absatz- und Tabellenstruktur ist ungeprüft.** `fundstellen.zerlege` erwartet die
   Struktur, die `auslesen` aus dem Text herstellt. Ob Vision-Zeilenobservationen dieselbe
   Absatztrennung tragen, ist **nicht gemessen** — der Vergleich hier hat nur Zeichen, Wörter
   und Zahlen betrachtet.
6. **Plattformbindung.** Vision ist macOS-only. Heute läuft der Auslese-Pfad überall, wo
   Tesseract installiert ist.

## Offen

* Die Punkte 1–6 oben sind **geplant, nicht gemessen**.
* Die Stichprobe stammt aus einem Korpus; ob die Reihenfolgeverzerrung bei anderen
  Dokumententypen ähnlich stark auftritt, ist nicht geprüft.
* Ein Qualitätsmaß, das Zeilenstruktur *bewusst* bewertet (statt sie zu ignorieren oder als
  Fehler zu zählen), fehlt weiterhin. F1 über Multimengen ignoriert Reihenfolge — das ist hier
  richtig, aber es heißt auch: eine Engine, die perfekt liest und völlig falsch sortiert,
  bekommt 1,0. Für den Assistenten zählt das Zitat am Ende doch an einer Stelle im Dokument.
