# Skript-Baustein: Welches Modell, welches Embedding — und warum du das selbst messen musst

> **Historisch, Stand 25.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


Notiz für das TelePro-Skript (Format nach `TelePro/SKRIPT-FORMAT.md`). Das ist der **Aufruf-Baustein**: Er erklärt
kurz, was gemessen wurde, nennt nur die Stolperfallen, die eine Entscheidung ändern, und endet mit dem Angebot.
Gehört ans Ende des Videos oder als eigener Block. Zahlen: `lokalki-lab/docs/messungen/2026-09-21-modellwahl-notebook.md`,
`retrieval-befund-2026-09-21.md`, GermanQuAD-Lauf 22.09.

---

# Die Frage, die mir alle stellen [TIME: 0:00]

„Welches Modell soll ich nehmen?"

Ich habe fünf Wochen lang gemessen, um dir sagen zu können: **Die Frage ist falsch gestellt.**

[PAUSE]

Nicht, weil es keine Antwort gibt. Sondern weil die Antwort von etwas abhängt, das nur du hast:
**deinen Dokumenten.**

# Was ich gemessen habe [TIME: 0:00]

Damit das keine Behauptung bleibt, kurz der Umfang:

**Achtzehn Modelle.** Von einem Modell mit anderthalb Milliarden Parametern bis zu einem mit dreißig.
Qwen, Gemma, Mistral, Granite, Phi, LFM — und die europäischen: EuroLLM, Teuken, Apertus.

**Vier Embedding-Modelle.** Drei Suchverfahren. Zwei Reranker.
Zwei Kontextgrößen, mit und ohne Denken, drei Runtimes.

Und jedes Modell zweimal geprüft: einmal im Labor gegen feste Aufgaben — und einmal an **echten Dokumenten**
mit Fragen, deren Antwort ich kenne. Zweihundert Dateien, siebenhundert Absätze, zwanzig Fragen.

[NOTE: Einblendung: 18 Modelle · 4 Embeddings · 3 Suchverfahren · 2 Reranker — Logos oder Namensliste]

Und weil eine Prüfung nichts taugt, die man sich selbst gebaut hat, habe ich am Ende **zweihundert Fragen genommen,
die echte Menschen gestellt haben** — ein öffentlicher deutscher Datensatz, an dem ich nichts geschrieben habe.

[PAUSE]

Dazu kam alles, was man sonst noch falsch einstellen kann, und ich sage es bewusst schnell, weil es für deine
Entscheidung **nicht** den Ausschlag gibt:

Wie viel Kontextfenster das Modell wirklich braucht — vier- oder sechzehntausend Tokens.
Ob Denkmodelle im Vorteil sind, wenn man ihnen das Denken abschaltet.
Wie viel Speicher die Laufzeitumgebung heimlich frisst — Ollama, llama.cpp, LM Studio, MLX von Apple.
Und wie man verhindert, dass ein Modell beim Testen schummelt, indem es die Lösung liest statt sie zu berechnen.

Vier Nächte Rechenzeit sind dabei für die Tonne gegangen. Aus jeder habe ich mehr gelernt als aus den erfolgreichen.
!!Aber für die Frage „welches Modell, welches Embedding" ändert nichts davon die Antwort!!.

[NOTE: Diese Liste nur antippen, NICHT vertiefen — das Publikum soll den Umfang sehen, nicht die Details.
Wer mehr will: `skript-baustein-journey.md` (die sieben Stationen), `skript-baustein-kontext-4k.md`,
`skript-baustein-suche.md`. Bei Bedarf als Einblendung: „Kontext · Denken · Runtime-Speicher · Messhygiene — Details im Kanal".]

# Drei Dinge, die deine Entscheidung ändern [TIME: 0:00]

Ich erspare dir die vierzig Sackgassen. Drei Befunde zählen.

## Erstens: Das beste Embedding gibt es nicht [TIME: 0:00]

Dasselbe Verfahren, zwei verschiedene Dokumentbestände.

Auf **meinen Rechnungen** gewinnt Qwen-Embedding: neunundsiebzig Prozent Treffer auf Platz eins, BGE-M3 nur einundsiebzig.
Auf den **öffentlichen Texten** dreht es sich um: BGE-M3 einundneunzig, Qwen nur zweiundachtzig.

[PAUSE]

!!Das ist kein kleiner Unterschied. Das ist eine umgekehrte Rangfolge!!.

Wer dir sagt „nimm Embedding X", hat auf *seinen* Daten gemessen. Nicht auf deinen.

[NOTE: Einblendung: zwei Balkenpaare, Pfeile kreuzen sich — „Rechnungen" vs „Wikipedia"]

## Zweitens: Die klassische Wortsuche ist nicht tot — aber sie hat ein Deutschproblem [TIME: 0:00]

BM25, die Suche aus den Neunzigern, fand auf den öffentlichen Texten **dreiundachtzig Prozent** der Antworten
auf Platz eins — fast so gut wie das beste KI-Embedding.

Auf meinen Rechnungen: **einundzwanzig Prozent.**

Der Grund steht in einem einzigen Beispiel: Ich frage nach der **Telefon**rechnung. Im Dokument steht
„Telefon" und „Rechnung" — zwei Wörter. Für die Wortsuche ein Fremdwort. Platz fünfundvierzig von siebenhundert.

Deutsche Komposita. Rechnungsnummern. Datumsformate. Das ist Geschäftspost, nicht Wikipedia.

Wenn deine Dokumente so aussehen wie meine, brauchst du das Embedding.
Wenn sie wie Fließtext aussehen, reicht vielleicht die Wortsuche — und die kostet nichts.

## Drittens: Was nicht eingeordnet ist, findest du nie [TIME: 0:00]

Das war meine größte Überraschung, und sie hat nichts mit Suche zu tun.

Zwei Modelle, derselbe Bestand, zweihundert Dokumente.
Das eine ordnet **hundertneunundfünfzig** davon sicher ein. Das andere nur **hundertsiebenundzwanzig**.

Zweiunddreißig Dokumente Unterschied. Die liegen dann im Eingang und warten — und sind für jede Suche unsichtbar,
egal wie gut dein Embedding ist.

[PAUSE]

!!Der Flaschenhals war nicht die Suche. Der Flaschenhals war das Einordnen!!.
Und da war das größere Modell klar besser: neunzig Prozent richtige Kategorien gegen dreiundsiebzig.

[NOTE: Einblendung: 159 vs 127 Dokumente im Index, Rest ausgegraut]

# Was daraus folgt — für dich, nicht für mich [TIME: 0:00]

Meine Konfiguration steht. Aber sie steht für **meinen** Bestand:
Handwerksrechnungen, Angebote, Verträge, ein Notebook mit vierundzwanzig Gigabyte.

Deine Dokumente sind andere. Verträge sind nicht Rechnungen, Gutachten sind nicht Protokolle,
und ein Bestand mit fünfzigtausend Seiten braucht etwas anderes als einer mit fünfhundert.

Die gute Nachricht: **Das Messen ist der einfache Teil.**
Du brauchst zwanzig Fragen, deren Antwort du kennst. Den Rest macht das Werkzeug — ohne Sprachmodell,
in Minuten, auf deinem eigenen Rechner. Und am Ende weißt du es, statt es zu glauben.

# Das Angebot [TIME: 0:00]

Genau das mache ich beruflich: **für einen konkreten Dokumentenbestand herausfinden, welches Modell und welches
Embedding tatsächlich funktionieren** — gemessen, nicht geraten. Auf eurer Hardware, mit euren Dokumenten,
alles lokal, nichts verlässt das Haus.

Wenn du gerade überlegst, ob lokale KI für euch taugt, oder wenn ihr schon etwas aufgebaut habt und nicht wisst,
warum es nicht trifft: !!schreib mir!!. Kontakt steht in der Beschreibung.

[NOTE: Einblendung Kontakt/Website; CTA-Karte]

Und wenn du es selbst machen willst — das Werkzeug liegt offen. Link ebenfalls unten.

---

## Quellen (nicht sprechen)

- 18 Modelle, Lab + Lasttest: `lokalki-lab/docs/messungen/2026-09-21-modellwahl-notebook.md` (Nachträge 1–3).
- Embedding-Umkehr: malerbetrieb Stufe 200 (694 Absätze, 14 Fragen) dense R@1 qwen3-embedding 79 / bge-m3 71;
  GermanQuAD (474 Absätze, 200 menschliche Fragen, 22.09.) dense R@1 bge-m3 91 / qwen3-embedding 82.
- BM25: malerbetrieb R@1 21 / R@8 43; GermanQuAD R@1 83 / R@8 96. „Telefonrechnung" Rang 45, Ursache im
  `retrieval-befund-2026-09-21.md` (Kompositum + Stoppwörter + Längennormierung b = 0,75).
- Einordnen: gemma4:12b 159/163 soll-sichere Dateien im Index, Kategorie 90 %, Belege ungültig 1,9 %;
  qwen3.5:4b 127/163, Kategorie 73 %, Belege 6,1 % (Lasttest Stufe 200, 21./22.09.).
- GermanQuAD: deepset/germanquad über den MTEB-Spiegel, CC-BY-4.0, abgerufen 22.09.2026 —
  Fragen UND Texte von Dritten, `beweise/germanquad/README.md`.
- Nur genannt, nicht vertieft (Abschnitt „Was ich gemessen habe"), mit den Zahlen dahinter:
  - **Kontext:** Runner-Log 2 675 echte Anfragen, Median 146 Token, Max 3 027 -> 4k reicht; Trefferzahlen unter
    4k und 16k identisch (Suite 3.4, Kontext als Messbedingung). `skript-baustein-kontext-4k.md`.
  - **Denken:** qwen3:4b legt bei `think:false` das Denken auf Englisch in die Antwort (74/74 Fälle,
    2 700–4 400 Token) -> german 0/125; die reine Instruct-Variante schlägt es 21:0 beim Verdichten und läuft
    viermal schneller. Unter llama.cpp lässt sich das Denken gar nicht abschalten (Commit ac6f624).
  - **Runtime-Speicher:** der Zuwachs 3 -> 15 GB über eine Nacht war der Prompt-Cache von llama-server
    (`--cache-ram`, Standard 8192 MiB), kein Modellverhalten; mit `--cache-ram 0` flach über 50 Prompts.
    Fünf Runtime-Zeilen gemessen, Steckbrief-Werkzeug (`lab runtime`) qualifiziert jede Runtime in 8 Minuten.
    `docs/messungen/2026-09-20-prompt-cache-und-runtime-steckbriefe.md` (im Lab-Repo).
  - **MLX:** kein gemessener Vorteil auf dieser Maschine — 5–10 % mehr Tokens/s beim Generieren, aber im
    Assistenten viermal langsamer beim Einordnen (48 vs 10 s/Datei). Ursache nicht isoliert; dafür gibt es seit
    Runtime-Suite 1.2 die Prefill-Prüfung.
  - **Messhygiene/Sandbox:** die Praxisaufgaben laufen in einer Sandbox, die dem Modell das Lesen des Maßstabs
    verwehrt; vier Angriffe wurden live gemessen, bevor die heutige Form hielt (CLAUDE.md im Lab-Repo).
  - **Vier verlorene Nächte:** Nacht A (Mac ist eingeschlafen), Nacht V1 (Prompt-Cache, Ergebnisse den Modellen
    zugeschrieben), der qwen3:4b-Lauf mit unwirksamem `think:false`, der abgebrochene GermanQuAD-Lauf
    (Logdatei auf abgezogener SSD). Erzählt in `skript-baustein-journey.md`.
