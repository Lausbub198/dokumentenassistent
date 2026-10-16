# Malerbetrieb Hoffmann — Demo-Stapel (25 Dateien)

Die Stufe 25 aus `../malerbetrieb/golden.json` (`stufen["25"]`), bytegleich kopiert.

**Stand 24.09.2026 — Konfiguration gewechselt.** Die Demo laeuft jetzt mit `gemma4:12b-it-q4_K_M`,
`qwen3-embedding:0.6b`, Reranker `bge-reranker-v2-m3` (k=20), `top_n: 5` und `kontext: 16384`. Einordnen
dauert damit grob 6 Minuten fuer die 23 nicht-doppelten Dateien (14,9 s je Datei gemessen bei Stufe 200).
Vor dem Trockenlauf: `uv sync --extra reranker` und die alte Zielablage loeschen (`rm -rf /tmp/da-ziel-demo`) --
das Embedding hat gewechselt, und ein alter Index liefert still falsche Treffer statt eines Fehlers.

**Was sich dadurch in der Demo aendert (im Trockenlauf pruefen):** Der 30-Seiten-`Rahmenvertrag_Geruestbau.pdf`
blieb mit dem alten 4096er-Kontext "unklar", weil sein Prompt (rund 6.278 Tokens) still gekuerzt wurde. Bei
Stufe 200 wird er mit 16384 jetzt "sicher" -- allerdings in der falschen Kategorie (Eingangsrechnungen statt
Vertraege; der Typ "Vertrag" stimmt). Wenn das im Demo-Stapel genauso passiert, ist das kein Problem, sondern
der beste Moment fuer den Nacharbeit-Satz: sicher eingeordnet, trotzdem falsch abgelegt, und genau deshalb
schaut ein Mensch drauf. Klick 8 im Skript (unklare Zeilen zeigen) stuetzt sich unabhaengig davon auf
`Untitled.pdf` und ein schiefes Foto -- die bleiben "unklar", weil sie an der OCR-Schwelle haengen.

Enthält: 2 Konfliktpaare (Farben Meister FM-2025-00231/00298: 1.289,25 gegen 1.170,25 EUR; Geruestbau Vogel GV 25/0067/0081: 4.998,00 gegen 3.998,40 EUR), 2 Duplikate (Rechnung_Farben_Maerz.pdf, Vertrag.pdf), 3 OCR-unsichere Fotos/Scans, 1 sachfremde Datei (Untitled.pdf), 30-Seiten-Rahmenvertrag, Notizen, Wiki, DOCX-Angebot.

Zweck fuer das Profil: "Alle Unterlagen der Malerbetrieb Hoffmann GmbH aus dem Geschaeftsjahr 2025 fuer Buchhaltung und Steuerberater ordnen"

Fragen fuer Finden (Sollwerte in golden.json, `ab_stufe <= 25`):
- Was kostet die Fassadenfarbe fuer die Ringstrasse 8 laut korrigierter Rechnung von Farben Meister? -> 1.170,25 EUR, Rechnung (9).pdf
- Welcher Betrag gilt fuer das Geruest Ringstrasse 8 nach der Korrekturrechnung von Vogel? -> 3.998,40 EUR, Rechnung (6).pdf
- Wann ist der Betriebsurlaub 2025? -> 28.07. bis 08.08.2025, Besprechung_Maerz.txt
- Was steht im Kaufvertrag fuer den Bagger? -> nicht gefunden

Start:

```bash
uv run dokumentenassistent --quelle beispiele/malerbetrieb-demo/Quelle --ziel /tmp/da-ziel-demo
```
