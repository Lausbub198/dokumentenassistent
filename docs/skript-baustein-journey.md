# Skript-Baustein: Die Reise — was wir getestet haben und was dabei herauskam

> **Historisch, Stand 25.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


Notiz für das TelePro-Skript (Format nach `TelePro/SKRIPT-FORMAT.md`). Erzählstück, das vor den beiden
Technik-Bausteinen (`skript-baustein-suche.md`, `skript-baustein-kontext-4k.md`) stehen kann oder als eigener Block
„Was ich in fünf Wochen gelernt habe". Zeitraum 18.08.–21.09.2026, 375 Commits an 17 Tagen, alle Zahlen aus
`lokalki-lab/docs/messungen/` und den privaten Lauf-Ordnern (`DOKASS_LAEUFE`). Stand 21.09. früh — Validierung, Retrieval-Eval
und Nacht (Stufe 100/200) sind gemessen.

Roter Faden: **Jede Station ist ein Irrtum, den eine Messung korrigiert hat.** Nicht „wir haben das beste Modell
gefunden", sondern „wir haben gelernt, was man messen muss, bevor man überhaupt ein Modell vergleichen darf".

---

# Die Frage, mit der alles anfing 

Es gibt hunderttausend offene Sprachmodelle.
Welches läuft auf **meinem** Notebook — 24 Gigabyte, kein Server, kein Netz — so gut, dass ich meinem
Dokumentenassistenten vertrauen kann?

Die Antwort im Internet: Leaderboards. Ranglisten. Punktzahlen.
Ich habe fünf Wochen gebraucht, um zu verstehen, warum die mir **nichts** sagen.

[PAUSE]

Hier ist, was stattdessen passiert ist. Sieben Stationen.

# Station 1: Der erste Messstand — und die erste Lektion 

August. Ich baue ein Prüflabor: sechs Prüfungen, die jedes Modell bestehen muss.
Startet es überhaupt? Frisst es den Speicher? Wie schnell? Kann es Deutsch? Kann es JSON? Kann es Werkzeuge aufrufen?

Und eine harte Regel von Anfang an: **Kein Sprachmodell steuert die Messung.** Ein stures Programm startet, stoppt,
misst, bewertet. Reproduzierbar oder wertlos.

Erste Lektion nach zwei Tagen: **Einmal messen ist nicht messen.**
Jeder Lauf war ein einzelner Wert. Ab da: dreimal, Median, Min, Max. Und der beste Wert ist niemals die Schlagzeile.

[NOTE: Einblendung: sechs Gates als Kacheln — startability, memory, speed, german, json, tools]

# Station 2: Der Mensch als Richter — und warum er versagt 

Ich wollte die deutsche Sprachqualität bewerten. Note 1 bis 4.
Ergebnis: Zwei Modelle, 23 und 24 von 24 Punkten. Praktisch gleich.

Dann habe ich die Antworten **nebeneinander** gelegt. Dieselbe Aufgabe, beide Antworten.
Und plötzlich waren sie nicht gleich. Das eine hatte eine Liste geliefert, wo Fließtext verlangt war.
Alle automatischen Prüfungen: bestanden.

[PAUSE]

Lektion zwei: !!Eine absolute Note ist unkalibriert!!. Derselbe Mensch urteilt anders, sobald er ein zweites Modell
gesehen hat. Seitdem gibt es keine Noten mehr — nur Frage und Antworten nebeneinander. Das Urteil bleibt beim Menschen,
aber er sieht, was er vergleicht.

# Station 3: Das große Modell, das nicht rechnet 

Qwen3.8 mit 27 Milliarden Parametern. 17 Gigabyte. Passt in 24.
Das Lab meldete: startet nicht. Ich las: läuft nicht auf dieser Maschine.

**Falsch.** Das Protokoll sagte: Modell geladen — ja. Antwort — HTTP 500, Compute error.
Es *lädt*, aber es *rechnet* nicht. Der Speicher reichte fürs Modell, nicht für Modell plus Kontext plus System.

Lektion drei: **Die Grenze des Notebooks liegt nicht bei der Modellgröße.** Sie liegt bei Modell plus Kontextfenster
plus allem, was sonst läuft. 24 Gigabyte heißt: unter zehn Gigabyte Modell, sonst kippt es.

[NOTE: Einblendung: 17 GB Modell + KV-Cache + System > 24 GB]

# Station 4: Die Nacht, die nichts wert war 

September. Ich lasse eine ganze Nacht laufen. Mehrere Modelle, alle Prüfungen.
Morgens: Speicher von 3 auf 15 Gigabyte gewachsen, Swap voll, Ergebnisse unbrauchbar.

Erster Reflex: Die Modelle sind zu groß.
Zweiter Blick: Alle Modelle wachsen gleich. Bei *jedem neuen Prompt* etwa 94 Megabyte. Bei *wiederholten* Prompts: nichts.

[PAUSE]

Das war kein Modell. Das war die **Runtime** — der Prompt-Cache von llama-server, acht Gigabyte Standard, den Ollama
nicht abschaltbar macht. Mit `--cache-ram 0` unter llama.cpp: flach wie ein Brett, 50 verschiedene Prompts, 2,4 Gigabyte.

Lektion vier, die wichtigste: !!Modell ist nicht gleich Runtime!!. Dasselbe Modell verhält sich unter Ollama, llama.cpp
und LM Studio verschieden — nicht in der Antwort, aber im Speicher. Wer Ollama-Ergebnisse dem Modell zuschreibt, misst
falsch.

Seitdem: **Kein Modelltest ohne Runtime-Steckbrief.** Acht Prüfungen, acht Minuten, bevor irgendein Modell antreten darf.
Ist die Runtime krank, gibt es keine Nacht. Fünf Runtime-Zeilen gemessen: drei wachsen, eine — MLX unter LM Studio —
bleibt stabil, eine ist auf dieser Version nicht messbar.

[NOTE: Einblendung Runtime-Tabelle aus `docs/messungen/2026-09-20-prompt-cache-und-runtime-steckbriefe.md`]

# Station 5: Äpfel und Birnen 

Jetzt endlich Modelle vergleichen. Erste Runde: vierzehn Kandidaten.
Und ich merke beim Lesen: Die einen **denken** vor der Antwort — Qwen3 schreibt erst tausend Wörter Überlegung —,
die anderen antworten direkt.

Das ist kein Vergleich. Wer denkt, braucht fünfmal länger und trifft öfter. Also: **alle ohne Denken.**

Und dann die Überraschung: qwen3:4b mit ausgeschaltetem Denken denkt trotzdem.
Auf Englisch. Mitten in der Antwort. „Okay, let's tackle this query…" — und dann erst Deutsch.
Vierundsiebzig von vierundsiebzig Antworten. Das Modell kann nicht *nicht* denken; der Schalter nimmt ihm nur den Rahmen.

[PAUSE]

Lektion fünf: **Ein RAG braucht kein Modell, das denkt. Es braucht eines, das lesen kann.**
Denkmodelle sind für Rätsel. Mein Assistent stellt keine — er legt acht Absätze hin und sagt: lies, entnimm, belege.
Die reine Instruct-Variante desselben Modells, qwen3:4b-instruct, hat das Denkmodell in der Bedingung „ohne Denken"
um Längen geschlagen: 21 zu 0 beim Verdichten, 13 zu 0 beim Nachfragen — und läuft viermal schneller.

[NOTE: Einblendung: qwen3:4b think:false → „Okay, let's tackle this query…" als Screenshot]

# Station 6: Wie viel Kontext braucht ein RAG wirklich? 

Die deutschen Modelle — EuroLLM, Teuken — fielen durch, bevor sie ein Wort gesagt hatten. Grund: Sie können nur
4 000 Tokens Kontext, meine Prüfung verlangte 16 000.

Wer sagt, dass es 16 000 sein müssen? Ich habe nachgezählt, was mein Assistent wirklich schickt:
2 675 echte Anfragen. Median **146 Tokens**. Maximum 3 027.

Also: Kontext wird eine **Messbedingung**, keine Vorgabe. Dieselbe Prüfung, zwei Stufen — 16k und 4k.
Und plötzlich sind EuroLLM und Teuken messbar. Ergebnis: sie fallen trotzdem durch — kein Werkzeugaufruf, Teuken
findet kaum eine Zahl. Die Sprache allein rettet ein Modell nicht.

Lektion sechs: **Miss, was dein System wirklich braucht — nicht, was das Modell könnte.**
Und: Kleiner Kontext ist kein Nachteil, wenn der Retriever gut ist. Mehr dazu im Baustein Suche.

[NOTE: hier Übergang zu `skript-baustein-kontext-4k.md` möglich]

# Station 7: Beweisen statt behaupten 

Jetzt habe ich eine Tabelle. Vierzehn Modelle, zwei Runtimes, zwei Kontextstufen, mit und ohne Denken.
Drei Kandidaten liegen vorn: qwen3:4b-instruct, granite4.1:8b, Ministral-8B. Ein viertes, qwen3.5:9b, als Denkmodell
mit funktionierendem Schalter.

Aber die Tabelle beweist nichts. Sie sagt, wie die Modelle auf **meinen Prüfaufgaben** abschneiden.
Ob sie auf **meinen Dokumenten** besser arbeiten, sagt sie nicht.

[PAUSE]

Deshalb der letzte Schritt: Alle vierzehn laufen im echten Assistenten, auf 25 echten Dateien, mit zwölf Fragen, deren
Antwort ich kenne. Und parallel messe ich den Retriever getrennt — drei Embedding-Modelle, Wortsuche, Bedeutungssuche,
beides zusammen — ohne Sprachmodell.

Stimmt die Reihenfolge des Labors mit der Reihenfolge auf dem eigenen Korpus überein, dann misst das Labor das Richtige.
Stimmt sie nicht, weiß ich, welche Prüfung falsch misst.

Die Validierung hat die Reihenfolge des Labors **teilweise** bestätigt — und an einer Stelle widerlegt.
Bestätigt: qwen3.5:9b vorn, gemma4 dahinter. Widerlegt: zwei Modelle, die im Labor auf Platz 2 und 3 standen, erfinden auf
echten Dokumenten jedes vierte bis sechste Zitat. Das Labor hatte keine Prüfung dafür. Jetzt weiß ich, welche fehlt.

Und der Retriever, getrennt gemessen: Bei 25 Dateien trifft jedes Embedding. Bei 200 findet nomic-embed-text nur noch
29 Prozent der Antworten auf Platz 1, qwen3-embedding 79. Und meine Wortsuche — BM25, das Verfahren, auf das ich stolz
war — versagt an deutschen Komposita: „Telefonrechnung" gegen „Telefon" plus „Rechnung", Platz 45.

[PAUSE]

Ohne die Messung hätte ich beides dem Sprachmodell zugeschrieben.

Und dann die Nacht: dieselben vier Modelle, die sauber zitieren, auf 200 statt 25 Dateien.
Das Modell, das ich um Mitternacht empfohlen hätte — gemma4:e4b, 88 Prozent richtige Kategorien —, ordnet bei 200 Dateien
noch **11 Prozent** richtig zu. Bei 25 Dateien war das unsichtbar.

[PAUSE]

Übrig blieben drei, und keins gewinnt alles:
qwen3.5:4b — drei Gigabyte, sieben Sekunden pro Datei, die meisten richtigen Antworten.
qwen3.5:9b — alle acht Widersprüche zwischen Dokumenten erkannt.
gemma4:12b — neunzig Prozent richtige Kategorien, zwei Prozent falsche Belege — und doppelt so langsam.

Naheliegend wäre: zwei Modelle. Ein schnelles für Fragen, ein gründliches fürs Einordnen.
Ich habe es gebaut — und dann gemessen, ob es etwas bringt.

[PAUSE]

**Es bringt nichts.** Das große Modell allein beantwortet sechzehn von zwanzig Fragen, mit dem schnellen Sucher davor
fünfzehn. Der Unterschied ist Rauschen. Gespart hat die Aufteilung vier von hundertsechzehn Minuten — und gekostet
hat sie einen zweiten Ladevorgang und eine Stelle mehr, an der man etwas falsch konfigurieren kann.

Also doch ein Modell. Aber nicht, weil es einfacher ist, sondern weil zwei nachweislich nichts gebracht haben.

[NOTE: Stand 23.09.2026, `beweise/last/2026-09-22/` und `2026-09-23/`. Die Entscheidung fiel gegen die eigene
Erwartung — der Satz „naheliegend wäre zwei" gehört ins Video, weil die Widerlegung die Pointe ist.]

[NOTE: Einblendung Validierungs-Tabelle `beweise/last/2026-09-20/bericht.md` (14 Modelle, Stufe 25), Nacht-Tabelle
`beweise/last/2026-09-21/bericht.md` (Stufe 100/200) und Retrieval-Tabelle `beweise/retrieval/2026-09-21/bericht.md`.
Gesamtauswertung: `lokalki-lab/docs/messungen/2026-09-21-modellwahl-notebook.md`. Zahlen Stufe 200: qwen3.5:4b 16/20,
73 %, 6,1 %, 3/8 Konflikte, 7,8 s/Datei; qwen3.5:9b 14/20, 83 %, 2,7 %, 8/8, 12,6 s; gemma4:12b 16/20, 90 %, 1,9 %, 8/8,
16,1 s; gemma4:e4b 13/20, 11 %, 7,2 %, 6/8.]

# Was ich mitnehme 

Sieben Lektionen, eine je Station:

Eins: Einmal messen ist nicht messen.
Zwei: Eine absolute Note ist unkalibriert — vergleiche nebeneinander.
Drei: Die Grenze ist Modell plus Kontext plus System, nicht die Modellgröße.
Vier: !!Modell ist nicht gleich Runtime!! — erst die Runtime qualifizieren.
Fünf: Ein RAG braucht kein Modell, das denkt, sondern eines, das lesen kann.
Sechs: Miss, was dein System wirklich schickt.
Sieben: Eine Prüfung beweist erst etwas, wenn sie gegen die Wirklichkeit gehalten wurde — und zwar in der Größe, die die Wirklichkeit hat.

[PAUSE]

Und die Meta-Lektion über allen: Fast jede dieser Erkenntnisse hat eine Nacht Rechenzeit gekostet, die nichts wert war.
!!Das Teure am lokalen KI-Betrieb sind nicht die Modelle. Es sind die falschen Schlüsse!!.

---

## Quellen (nicht sprechen)

> **Pfade:** `docs/messungen/…` und `lab/…` liegen im **Lab-Repo** (`../lokalki-lab/`), nicht hier.
> Der Dokumentenassistent hat überhaupt kein `docs/messungen/`. Korrigiert 24.09.2026 — von diesem
> Projekt aus gelesen liefen alle diese Verweise ins Leere.

- Station 1: `docs/messungen/2026-08-20-reproduzierbarkeit.md`, `2026-08-20-wiederholungen.md` (Suite 1.11, n=1 → 3×).
- Station 2: `docs/messungen/2026-08-22-antwortvergleich.md`; `lab/vergleich.py` (Docstring: 23 vs 24 von 24, Liste
  statt Fließtext).
- Station 3: `docs/messungen/2026-08-22-qwen38-27b-ctx-band.md` (Qwen3.8-27B UD-Q4_K_M 17 GB, Ollama 0.32.5,
  model_load ok, chat_response http_500).
- Station 4: `docs/messungen/2026-09-20-prompt-cache-und-runtime-steckbriefe.md`; Nacht V1 19./20.09.; Steckbrief
  `runtime-ollama-0.34.0-20260919T181031Z` (~94 MB je neuem Prompt, 100 Prompts 5,3 → 11,0 GB); core `--cache-ram 0`
  2 393–2 401 MB über 50 Prompts. Runtime-Suite 1.1, 8 Prüfungen, `--kurz` ~8 min.
- Station 5: `docs/messungen/2026-09-20-screening-ohne-denken.md` (S2: 74/74, 2,7–4,4k Tokens; Instruct 21/13 vs 0/0);
  Commit ac6f624 (core kann Denken nicht abschalten). Zeitfaktor: Speed-Fall long 51 s (Denken) vs ~13 s (Instruct).
- Station 6: Runner-Log 2 675 Anfragen, Median 146 / P99 2 491 / Max 3 027; Suite 3.4 Kontextstufen (Commits
  81976d1, 23f3dbe); S3 core 20.09. 16:28–18:32: EuroLLM Werkzeugwahl 0/25, Teuken Verdichtung 1/25.
- Station 7: `lab uebersicht` (Commit d566f5e); Lasttest `beweise/last/`, Retrieval-Eval `beweise/retrieval/` — Zahlen
  offen bis zum Lauf.
- Rahmen: 371 Commits, 18.08.–20.09.2026, `git log` lokalki-lab.
