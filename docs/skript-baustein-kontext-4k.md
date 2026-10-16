# Skript-Baustein: 4k oder 16k Kontext? [TIME: 0:00]

> **Historisch, Stand 25.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


Notiz für das TelePro-Skript (Format nach `TelePro/SKRIPT-FORMAT.md`). Zahlen gemessen am 2026-09-20 im LocalKI Lab
(Ollama-Runner-Log: 2 675 echte Anfragen des Dokumentenassistenten; Runtime-Steckbriefe; Screening S1/S2).

# Wie viel Kontext braucht ein lokales RAG wirklich? [TIME: 0:00]

Jeder redet über Kontextfenster: 32k, 128k, eine Million Tokens.
Ich habe nachgemessen, was mein Dokumentenassistent gestern **tatsächlich** an das Modell geschickt hat.
Zweitausendsechshundert Anfragen.

[PAUSE]

Der Median: **146 Tokens**.
Neunundneunzig Prozent unter 2 500.
Das Maximum: 3 027.

Mein RAG lebt in !!vier tausend Tokens!! — mit tausend Reserve.

[NOTE: Einblendung Tabelle Median/P90/P99/Max]

# Was man mit 4k gewinnt [TIME: 0:00]

Der Speicher für den Kontext, der KV-Cache, schrumpft auf ein Viertel.
Die Anfrage wird schneller verarbeitet.
Und auf einem 24-Gigabyte-Notebook bleibt neben dem Modell wieder Platz für alles andere.

Dazu kommt: **mehr Modelle** kommen in Frage.
Die deutsch trainierten Modelle — EuroLLM, Teuken — können nur 4k.
Bei 16k fallen sie durch, bevor sie ein Wort Deutsch gesagt haben.

# Was man mit 4k verliert [TIME: 0:00]

Drei Dinge.

Erstens: **kein ganzes Dokument** mehr im Prompt. Eine zwanzigseitige Richtlinie passt nicht — nur ihre Absätze.
Das RAG muss also treffsicher abrufen, statt „alles rein und das Modell sucht".

Zweitens: **keine Reserve für Zweifel**. Bei 16k schickt man zehn Treffer mit, bei 4k fünf.
Der Retriever wird zum Nadelöhr — wenn der falsche Absatz oben steht, hat das Modell keine Chance.

Drittens: **lange Werkzeugketten**. Frage, Werkzeugaufruf, Ergebnis, zweiter Aufruf, Antwort — jeder Schritt bleibt im Kontext.
Bei mehr als zwei Runden wird es eng.

[PAUSE]

Und eine Falle, die bei 4k viel früher zuschlägt:
Ollama kürzt einen zu langen Prompt **still**. Kein Fehler, keine Warnung — das Modell antwortet auf einen halben Text.
Gemessen: 33 770 Tokens geschickt, 8 194 angekommen.
Bei 4k passiert das schon ab dem sechsten Absatz.

# Wann 4k reicht — und wann nicht [TIME: 0:00]

4k reicht, wenn drei Bedingungen stimmen:
die Antworten sind kurz — Belege, Kategorien, Fristen, nicht Aufsätze;
der Retriever liefert die richtigen zwei bis fünf Absätze;
und du prüfst die Zitate gegen das Original — so wie der Assistent es tut.

16k brauchst du, wenn ganze Dokumente verglichen werden — „unterscheidet sich Vertrag A von Vertrag B?" —
oder wenn das Modell den Überblick über einen langen Vorgang behalten muss.

[NOTE: Regel für die Einblendung: Belegfragen → 4k. Dokumentvergleich → 16k.]

Meine Regel: !!Miss, was dein RAG wirklich schickt!! — nicht, was das Modell könnte.
Bei mir waren es 146 Tokens im Median. Das Kontextfenster war nie das Problem.

---

## Quellen (nicht sprechen)

- Prompt-Längen: `~/.ollama/logs/server.log`, Zeilen `new prompt, n_ctx_slot = 4096 … task.n_tokens = N`, 2026-09-19/20,
  2 675 Anfragen (Slot 4096 = Dokumentenassistent). Median 146, P90 1 115, P99 2 491, Max 3 027.
- Stille Kürzung: Runtime-Steckbrief `runtime-ollama-0.34.0-20260919T181031Z`, Prüfung `kontextgrenze`
  (`prompt_tokens 8194`, `prompt_tokens_erwartet 33770`).
- 4k-Modelle: Screening S1 (2026-09-20), EuroLLM-9B und Teuken-7B `num_ctx_unsupported` bei 16 384.
- Suite 3.4 (`lokalki-lab`, Kontextstufe als Messbedingung `--kontext 4096|16384`, eine Suite, keine Variante) und
  Screening S3 messen alle Kandidaten unter 4k ohne Denken.
