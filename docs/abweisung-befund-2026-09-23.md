# Abweisung: trennt ein Score beantwortbare von unbeantwortbaren Fragen? (23.09.2026)

> **Historisch, Stand 23.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


## Was geprüft werden sollte

Am 22.09. sah es auf `beispiele/malerbetrieb` Stufe 200 so aus, als trenne **kein**
Retrieval-Score die beantwortbaren von den unbeantwortbaren Fragen, **jeder Reranker-Score
aber schon**: Kosinus qwen3-embedding 0.5062 gegen 0.5161 (überlappt), Kosinus bge-m3 0.4965
gegen 0.5613 (überlappt), BM25 8.74 gegen 10.48, RRF 0.0253 gegen 0.0323 — alle überlappen;
bge-reranker-v2-m3 0.0592 gegen 0.0080 (Faktor 7, trennt), Qwen3-Reranker 5.13 gegen 3.63
(trennt).

Die Stichprobe war **14 beantwortbare gegen 6 unbeantwortbare** Fragen. Das reicht für eine
Beobachtung, nicht für eine Schwelle im Produkt. Diese Runde sollte dieselbe Frage mit großer
Stichprobe beantworten.

## Was gemessen wurde — und was nicht

| Lauf | Stand |
|---|---|
| malerbetrieb Stufe 200, 32 Fälle, bge-m3 + qwen3-embedding:0.6b, bge-reranker-v2-m3 k=8/20, mps | **gemessen** (23.09., `beweise/abweisung/2026-09-23/`) |
| GermanQuAD 150+150 (bzw. 250+250), dieselben Signale, CPU | **nicht gemessen** (abgebrochen 23.09. 09:36, Maschine pausiert) |

Für GermanQuAD liegt **keine einzige Ergebniszeile** vor (`grep -c germanquad
abweisung-scores.jsonl` → 0; `abweisung.jsonl` → 0). Es steht deshalb unten keine Zahl, keine
Schätzung und kein Teilergebnis für diesen Korpus. Die Zahlen dieses Dokuments gelten
ausschließlich für malerbetrieb.

## Methode: unbeantwortbar entsteht durch Weglassen

Unbeantwortbare Fragen muss man nicht erfinden — man kann sie erzeugen. Entfernt man das
Zieldokument einer beantwortbaren Frage aus dem Bestand, ist sie dort nicht mehr zu
beantworten, und die Frage bleibt so formuliert, wie sie vorher war. Es entsteht kein neuer
Autorenschafts-Bias durch jemanden, der sich „unbeantwortbare" Fragen ausdenkt — genau so sind
die sechs ursprünglichen Negative entstanden.

malerbetrieb Stufe 200 hat damit drei Gruppen:

| Klasse | Herkunft | Anzahl |
|---|---|---|
| `beantwortbar` | golden-Fragen mit `status: gefunden` | 14 |
| `unbeantwortbar` (themenfremd) | golden-Fragen mit `status: nicht_gefunden` | **4** |
| `unbeantwortbar` (Weglassen) | dieselben 14 Fragen, je ohne ihre Zieldatei | 14 |

**Korrektur zur Auftragsannahme:** Stufe 200 hat **4** `nicht_gefunden`-Fragen, nicht 6
(Alarmanlage, Dachdecker, Photovoltaik, Bagger). malerbetrieb kommt damit auf 14 + 4 + 14 =
**32** Fälle, nicht 34.

Weggelassen wird die **ganze Zieldatei**, nicht ein Absatz: `golden.json` nennt nur die Datei,
und bliebe ein Absatz derselben Rechnung stehen, wäre die Frage weiterhin beantwortbar.
Weggelassen wird **je Fall**, nicht global — zeigen zwei Fragen auf dieselbe Datei, stört das
nichts.

Eine Näherung, ausdrücklich benannt: BM25 wird einmal über den vollen Bestand gerechnet und
der weggelassene Absatz danach aus der Rangliste gestrichen. Exakt wäre, den Bestand vorher zu
verkleinern; IDF und mittlere Dokumentlänge verschieben sich dadurch minimal. Kosinus, RRF und
Reranker sind unberührt — sie bewerten je Absatz unabhängig, das Streichen ist dort exakt.

## Ergebnis malerbetrieb, Stufe 200 (14 beantwortbar gegen 18 unbeantwortbar)

Rangfolge nach ROC-AUC (selbst implementiert, Mann-Whitney-Form, an Handbeispielen geprüft —
kein sklearn).

| Signal | AUC | beste Schwelle | Genauigkeit % | Sensitivität % | Spezifität % | min beantw. / max unbeantw. | trennt | Schwelle bei 95 % Spez. | Verlust bei 95 % Spez. |
|---|---|---|---|---|---|---|---|---|---|
| rerank_bge-reranker-v2-m3_k20@qwen3-embedding:0.6b | 0.8433 | 0.9075 | 78 | 79 | 78 | 0.0592 / 0.9947 | nein | 0.9954 | 9/14 (64 %) |
| rerank_bge-reranker-v2-m3_k8@bge-m3 | 0.8393 | 0.9075 | 78 | 79 | 78 | 0.0592 / 0.9947 | nein | 0.9954 | 9/14 (64 %) |
| rerank_bge-reranker-v2-m3_k20@bge-m3 | 0.8353 | 0.9075 | 78 | 79 | 78 | 0.0592 / 0.9947 | nein | 0.9954 | 9/14 (64 %) |
| rerank_bge-reranker-v2-m3_k8@qwen3-embedding:0.6b | 0.8333 | 0.6099 | 75 | 93 | 61 | 0.0592 / 0.9947 | nein | 0.9954 | 9/14 (64 %) |
| dense@qwen3-embedding:0.6b | 0.7679 | 0.5476 | 72 | 79 | 67 | 0.5062 / 0.7402 | nein | 0.7445 | 13/14 (93 %) |
| dense@bge-m3 | 0.7579 | 0.6289 | 75 | 79 | 72 | 0.4965 / 0.7439 | nein | 0.7607 | 13/14 (93 %) |
| bm25 | 0.6806 | 14.4526 | 66 | 43 | 83 | 8.7382 / 20.5138 | nein | 22.3959 | 13/14 (93 %) |
| rrf@qwen3-embedding:0.6b | 0.6250 | 0.0325 | 66 | 50 | 78 | 0.0253 / 0.0328 | nein | 0.0328 | 14/14 (100 %) |
| rrf@bge-m3 | 0.6111 | 0.0253 | 59 | 100 | 28 | 0.0253 / 0.0328 | nein | 0.0328 | 14/14 (100 %) |

**Kein einziges Signal trennt** — auch der Reranker nicht. Sein niedrigster beantwortbarer Wert
ist 0.0592, sein höchster unbeantwortbarer 0.9947. Das ist nicht „überlappt knapp", das ist
vollständige Überlappung: der schlechteste echte Treffer liegt unter fast jedem falschen.

Die Spalte „Verlust bei 95 % Spezifität" ist die Zahl, die im Produkt zählt. Selbst der beste
Reranker-Aufbau verliert **9 von 14** beantwortbaren Fragen, wenn man die Schwelle so legt,
dass 95 % der unbeantwortbaren abgewiesen werden. Als Abweisungsmechanismus ist damit keines
der neun Signale brauchbar.

### Der Befund zerfällt nach Art der unbeantwortbaren Frage

Trennt man die 18 unbeantwortbaren Fragen nach Herkunft, wird sichtbar, was die Gesamtzahl
verdeckt:

| Signal | AUC gesamt (18) | AUC nur themenfremde Negative (4) | AUC nur Weglass-Negative (14) |
|---|---|---|---|
| rerank_bge-reranker-v2-m3_k20@qwen3-embedding:0.6b | 0.8433 | **1.0000** | 0.7985 |
| rerank_bge-reranker-v2-m3_k8@bge-m3 | 0.8393 | **1.0000** | 0.7934 |
| rerank_bge-reranker-v2-m3_k20@bge-m3 | 0.8353 | **1.0000** | 0.7883 |
| rerank_bge-reranker-v2-m3_k8@qwen3-embedding:0.6b | 0.8333 | **1.0000** | 0.7857 |
| dense@qwen3-embedding:0.6b | 0.7679 | 0.9643 | 0.7117 |
| dense@bge-m3 | 0.7579 | 0.9464 | 0.7041 |
| bm25 | 0.6806 | 0.9286 | 0.6097 |
| rrf@qwen3-embedding:0.6b | 0.6250 | 0.8214 | 0.5689 |
| rrf@bge-m3 | 0.6111 | 0.8304 | 0.5485 |

Der Befund vom 22.09. war **auf den vier themenfremden Fragen gemessen** — und dort stimmt er
exakt: der Reranker trennt sie perfekt (AUC 1.0, alle vier liegen unter 0.0592, dem
niedrigsten beantwortbaren Wert), die Retrieval-Scores nicht ganz (0.82–0.96). Gegen Fragen,
deren Zieldatei fehlt, während verwandte Dokumente im Bestand bleiben, bricht er ein: 0.79.
RRF fällt auf 0.55–0.57, also fast auf Münzwurf.

Die Rangfolge der Signale bleibt in beiden Spalten dieselbe — Reranker > dense > BM25 > RRF.
Das ist der belastbare Teil des Befunds.

### Warum der Reranker bei Weglass-Fragen hoch punktet

Die höchsten unbeantwortbaren Reranker-Werte (k=20 @ qwen3-embedding) sind keine Ausrutscher,
sondern erklärbar:

| Score | Frage (Zieldatei weggelassen) |
|---|---|
| 0.9947 | Was kostet die Fassadenfarbe für die Ringstraße 8 laut korrigierter Rechnung? |
| 0.9922 | Wann ist der Betriebsurlaub 2025? |
| 0.9922 | Wie viele Wochen Standzeit sind im Rahmenvertrag mit dem Gerüstbauer …? |
| 0.9295 | Welcher Betrag gilt für das Gerüst Ringstraße 8 nach der Korrekturrechnung? |

Nimmt man die Korrekturrechnung zur Ringstraße 8 aus dem Bestand, bleibt die
**Originalrechnung** zur Ringstraße 8 stehen. Der Cross-Encoder liest dort Frage und Absatz
gemeinsam und sieht zu Recht eine sehr gute Passung — nur steht dort der falsche Betrag. Das
ist kein Fehler des Rerankers, sondern die Bauart der Aufgabe: ein Score, der Ähnlichkeit
misst, kann „ähnlich, aber die falsche Rechnung" nicht von „richtig" unterscheiden.

Zum Vergleich die niedrigsten beantwortbaren Werte desselben Signals: 0.0592 (Rollgerüst
Bahnhofstraße 3), 0.6099 (Telefonrechnung März 2025), 0.7094 (Telefonrechnung Oktober 2025),
0.9075 (Kündigungsfrist Rahmenvertrag). Der echte Treffer mit 0.0592 liegt unter 13 der 18
unbeantwortbaren Fälle.

## Antwort auf die zwei Kernfragen

### (a) Trägt der Befund „Reranker trennt, Retrieval-Scores nicht" bei größerer Stichprobe?

**Teilweise, und in der scharfen Form nicht.** Für malerbetrieb, wo die Stichprobe von 20 auf
32 Fälle gewachsen ist:

- **Was hält:** die *Rangfolge*. Der Reranker ist auf beiden Arten von Negativen das beste der
  neun Signale (AUC 0.83–0.84 gegen 0.76–0.77 dense, 0.68 BM25, 0.61–0.63 RRF). Und auf genau
  den Fragen, an denen der Befund vom 22.09. gemessen wurde — themenfremde Fragen —, trennt er
  vollständig (AUC 1.0).
- **Was nicht hält:** die Aussage „der Reranker trennt". Über alle 18 unbeantwortbaren Fragen
  überlappen die Bereiche vollständig (0.0592 gegen 0.9947), und bei 95 % Spezifität kostet er
  9 von 14 echten Treffern. Der „Faktor 7" aus dem Befund ist ein Artefakt der Auswahl von
  Negativen, nicht eine Eigenschaft des Rerankers.
- **Was noch offen ist:** ob das auch bei *wirklich* großer Stichprobe und auf fremdem Text
  gilt. 14 gegen 18 ist besser als 14 gegen 6, aber immer noch klein, und malerbetrieb ist
  synthetisch. Der GermanQuAD-Lauf, der das beantworten sollte, fehlt (siehe unten).

### (b) Ist die Schwelle zwischen Beständen übertragbar?

**Nicht beantwortbar — der zweite Bestand fehlt.** Es gibt keine GermanQuAD-Zahl, gegen die
man eine malerbetrieb-Schwelle halten könnte.

Was die vorhandenen Daten aber schon zeigen: eine Schwelle ist **nicht einmal innerhalb
desselben Bestands zwischen Fragearten übertragbar**. Leitet man sie aus den vier themenfremden
Negativen ab, liegt sie irgendwo unter 0.0592 und über deren Höchstwert — sie lässt dann 100 %
der beantwortbaren Fragen durch und weist alle vier themenfremden ab, aber **keine einzige** der
14 Weglass-Fragen (deren niedrigster Wert bereits über 0.0592 liegt). Eine Schwelle, die an
einer Art von „nicht beantwortbar" kalibriert wurde, ist gegen die andere Art wirkungslos.

Das macht eine Übertragbarkeit zwischen Beständen unwahrscheinlich, **ist aber kein Beleg
dafür** — gemessen ist es nicht.

## Folge für `suche.py`

`suche.py` wurde nicht angefasst (Auftrag: erst messen, dann entscheiden). Die Messung stützt
diese Zurückhaltung: es gibt derzeit **kein Signal**, das eine Schwelle im Produkt rechtfertigt,
und der Reranker ist dafür kein besserer Kandidat als der Kosinus. Die heutige Arbeitsteilung —
Kosinus-Schwelle 0.49 als grober Vorfilter, Abweisung durch Modell plus Zitatprüfung — bleibt
damit unwiderlegt. Ob der Reranker im Produktpfad die *Rangfolge* verbessert, ist eine andere
Frage und in `docs/retrieval-befund-2026-09-21.md` positiv beantwortet; dieses Dokument sagt
nur, dass sein Score nicht als Abweisungskriterium taugt.

## Laufzeit: was diese Runde gekostet hat

| Lauf | Umfang | Zeit |
|---|---|---|
| Probe GermanQuAD | 10+10 Fragen, 2 Embeddings, k=8 und 20, CPU | **350 s** in der Messfunktion, 359 s inkl. Modell-Ladezeit |
| GermanQuAD 200+200 | 400 Fälle, 2 Embeddings, k=8 und 20, CPU | nach **76 min abgeräumt, ohne eine geschriebene Zeile** |
| malerbetrieb | 32 Fälle, 2 Embeddings, k=8 und 20, mps | lief durch |

Aus der Probe: rund **15 s je Fall** auf CPU bei zwei Embeddings und beiden k-Stufen — trotz
Zwischenspeicher, der jedes Paar (Frage, Absatz) nur einmal bewertet. 500 Fragen hätten damit
über zwei Stunden gebraucht; deshalb war der zweite Versuch auf 200+200 und der dritte auf
150+150 gesetzt. Beide kamen nicht ans Ziel.

**Empfehlung für die nächste Messung:**

1. **Zwischenergebnisse zeilenweise schreiben.** Das ist die wichtigste Lehre. Der Lauf
   schreibt heute erst am Ende — 76 Minuten Rechenzeit sind vollständig verloren, weil der
   Prozess kurz vor Schluss abgeräumt wurde. Jede fertige Fall-Zeile gehört sofort nach
   `abweisung-scores.jsonl`; die Auswertung kann daraus jederzeit nachgerechnet werden, auch
   aus einem halben Lauf.
2. **150+150 Fragen, k=8 und k=20, `--geraet cpu`.** Geschätzt 75–90 min. Nicht mehr — mps
   hängt bei langen GermanQuAD-Absätzen in `MPSStream::synchronize` (gemessen 22.09.), CPU ist
   dort der einzige Weg. Reicht die Zeit nicht, lieber k=20 weglassen als Fragen: k=8 und k=20
   lagen in der Probe gleichauf (beide AUC 1.0), die Fragenzahl ist die knappe Ressource.
3. **Fortschritt mitschreiben.** Ist eingebaut (alle 25 Fälle eine Zeile); ohne sie war beim
   ersten Abbruch nicht feststellbar, wie weit der Lauf war.
4. **Prozess wirklich ablösen.** `nohup … & disown` — `setsid` gibt es auf macOS nicht, und ein
   als Hintergrundaufgabe gestarteter Lauf wurde nach 76 min mit Code 144 beendet.
5. **Vor dem Start `ollama ps` prüfen.** Muster wie `pgrep -f "…lasttest"` treffen die eigene
   Wartezeile mit; ein Wartejob, der sich selbst findet, wartet ewig. `ps -eo command | grep
   "[p]ython -m …"` oder ein Blick auf `ollama ps` ist zuverlässiger.

## Offene Punkte

- **Der GermanQuAD-Lauf fehlt vollständig.** Er ist die einzige Messung, die (a) mit
  fremdgeschriebenen Fragen und großer Stichprobe und (b) mit einem zweiten Bestand beantworten
  kann. Aufwand: ein Lauf, 75–90 min, CPU, ohne Ollama-Konkurrenz.
- **Kontrollgruppe ist vorbereitet, aber ungenutzt.** Der GermanQuAD-Bestand hat 474 Absätze
  aus 233 Artikeln; bei 110 Artikeln besteht der Artikel aus genau einem Absatz. Nur dort nimmt
  das Weglassen den Artikel vollständig aus dem Bestand — sonst bleiben ein bis sechs
  Nachbarabsätze stehen, die die Frage womöglich doch beantworten. `abweisung.py` zählt das je
  Fall (`geschwister`) und schreibt es in jede Score-Zeile, damit der Befund für
  `geschwister == 0` getrennt nachgerechnet werden kann. Ohne Lauf liegt dazu nichts vor.
- **Qwen3-Reranker ist in dieser Runde nicht gemessen** (nur `BAAI/bge-reranker-v2-m3`), obwohl
  er im Befund vom 22.09. vorkommt.
- **Anzeigefehler in `verlust_bei_spezifitaet`.** Die Spalte „Verlust bei 95 % Spez." zählt die
  verlorenen Fragen gegen eine auf sechs Nachkommastellen **gerundete** Schwelle, die
  Sensitivität daneben gegen die ungerundete. Bei Wertgleichheit weichen beide voneinander ab:
  die beiden RRF-Zeilen meldeten im Rohbericht „9/14" bzw. „10/14" bei 100 % Verlust. In der
  Tabelle oben steht der aus der Sensitivität abgeleitete, richtige Wert (14/14). Die Zeilen
  aller anderen Signale sind in sich stimmig. Zu beheben, bevor die Zahl irgendwo zitiert wird:
  `verlorene` aus der Sensitivität ableiten statt neu zu vergleichen.
