# docs/

Dokumentation zum Dokumentenassistenten (Stand 2026-10-07).

> **Eine Quelle über allem:** `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`
> — Architektur mit Begründung je Baustein, Chronik aller Testreihen, gemessen Widerlegtes, Grenzen der
> Zahlen. Jede Leitzahl steht dort mit ihrem Messbericht.
>
> **Leitzahl:** 62 von 85 Fragen mit gültigem Beleg (73 %) am echten Bestand, 15 von 15 Abweisungen.
> Ausgangslage 24.09.: 22 von 85 (26 %). Gegenprobe GermanQuAD: 129 → 197 von 200.
>
> **Zwei Korpora nicht verwechseln:** Die meisten Zahlen in den älteren Dateien hier stammen aus dem
> **synthetischen Lasttest** (Malerbetrieb, 200 Dateien, 694 Absätze, 20 Fragen). Sie gelten dort
> weiterhin, sind aber nicht das Ergebnis des Projekts. Dateien, deren Befund überholt ist, tragen oben
> ein Banner „Historisch, Stand <Datum>".

- **`userstory.md`** — Kernstory (Malerbetrieb Hoffmann), Abnahmekriterien
  entlang des implementierten Ablaufs, plus 6 weitere Use Cases mit
  Sequenz-/Flowdiagrammen, jeweils markiert als implementiert oder Zielbild.
- **`systemlandschaft.md`** — Architekturdiagramm (Quelle → Pipeline →
  Zielablage/Protokoll → Web/MCP → Ollama, Bezug zum LocalKI Lab), Tabelle
  der angedockten Prozesse, Grenzen des Systems.

Alle Aussagen sind gegen `README.md`, `beispiele/*/README.md`,
`beweise/last/*/bericht.md`, `modelle.yaml` und die Modul-Docstrings unter
`src/dokumentenassistent/` geprüft; Zahlen tragen ihre Quelle inline.
