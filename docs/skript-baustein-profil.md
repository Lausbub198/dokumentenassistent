# Skript-Baustein: „Ich habe fünf Wochen das Modell optimiert. Der Fehler saß in einer Textdatei."

> **Historisch, Stand 25.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


Notiz für das TelePro-Skript (Format nach `TelePro/SKRIPT-FORMAT.md`). Das ist die **Klammer** um die
vier bestehenden Bausteine — sie erzählt den Praxistest vom 24.09.2026 und stellt die bisherigen
Zahlen richtig. Quelle aller Zahlen:
`../lokalki-lab/docs/messungen/2026-09-24-praxistest-echter-bestand.md`.

**Wichtig für die Aufnahme:** Der Bestand ist privat. Keine Dateinamen, keine Beträge, keine Namen
auf den Schirm. Wo Dokumente zu sehen sind: unkenntlich oder nachgebaut.

---

# Die Zahl, an die ich fünf Wochen geglaubt habe [TIME: 0:00]

Neunzig Prozent.

Zwanzig Fragen an meinen Dokumentenassistenten, achtzehn richtig beantwortet, jede mit Beleg.
Achtzehn Modelle verglichen, vier Embeddings, drei Suchverfahren, zwei Reranker. Vier Nächte
Rechenzeit in den Sand gesetzt und aus jeder was gelernt.

[PAUSE]

Dann habe ich es auf **meine eigenen Dokumente** losgelassen.

# Sechsundzwanzig [TIME: 0:00]

!!Sechsundzwanzig Prozent!!.

Nicht neunzig. Sechsundzwanzig.

[NOTE: Einblendung: großes „90 %" das zu „26 %" wird. Kein Hänger, harter Schnitt.]

Und bevor jetzt jemand sagt, ich hätte mir die Fragen schöngerechnet — umgekehrt:

Die hundert Fragen hat **nicht** das Werkzeug erzeugt, das geprüft wurde, sondern ein anderes
Sprachmodell aus meinen Dokumenten. Fünfzehn davon sind Fangfragen: plausibel klingende Fragen
zu Vorgängen, zu denen es **kein** Dokument gibt. Wer die beantwortet, erfindet.

Und ich habe nachgemessen, wie schwer die Fragen sind. Es gibt einen öffentlichen deutschen
Fragensatz, an dem Menschen die Fragen gestellt haben. Dort übernimmt eine Frage im Schnitt
**sechzig Prozent** ihrer Wörter direkt aus dem Absatz, in dem die Antwort steht. Bei meinen
Fragen: **elf Prozent.** Acht Fragen haben mit ihrem Zielabsatz **kein einziges** inhaltliches
Wort gemeinsam.

[NOTE: Einblendung: 0,60 vs 0,11 — zwei Balken]

Meine Prüfung war also nicht zu leicht. Sie war !!härter als der öffentliche Maßstab!!.

# Die Fangfragen hat es alle erkannt — und das ist keine gute Nachricht [TIME: 0:00]

Fünfzehn von fünfzehn abgewiesen. Hundert Prozent.

[PAUSE]

Klingt super. Ist es nicht.

Das System sagt bei **einundfünfzig von fünfundachtzig** beantwortbaren Fragen „nicht gefunden".
Wer so oft schweigt, erwischt natürlich auch jede Fangfrage. Das ist keine Trennschärfe.
Das ist Zurückhaltung.

!!Eine Abweisungsquote ohne die Trefferquote daneben ist eine Zahl, die nichts sagt!!.

# Die Fehlersuche — und meine erste Erklärung war falsch [TIME: 0:00]

Erster Verdacht: Der Prompt wird abgeschnitten. Ich gebe dem Modell pro Dokument nur die ersten
zweitausendvierhundert Wörter mit — eine Grenze aus einer Zeit, als das Kontextfenster viermal
kleiner war. Und tatsächlich: in vierzehn Fällen schreibt das Modell selbst in seine Begründung,
es habe nur einen Teil gesehen.

Klarer Fall, oder?

[PAUSE]

Nachgemessen: Von den dreiundvierzig Problemdokumenten hat das Modell **neunundzwanzig
vollständig gesehen**. Die Kürzungsrate liegt bei den Problemfällen bei dreiunddreißig Prozent —
bei den funktionierenden bei fünfundzwanzig. Das ist kein Unterschied, das ist Rauschen.

!!Hypothese tot!!. Hätte ich sie nicht gemessen, hätte ich einen halben Tag an der falschen
Schraube gedreht.

# Was wirklich los war [TIME: 0:00]

Der Assistent legt ein Dokument nur dann in den Index, wenn er **alles** über es belegen kann:
Kategorie, Dokumentart, Name — und jedes Pflichtfeld.

Und die Pflichtfelder lauteten: Datum, Aussteller, **Betrag**, **Rechnungsnummer**.

[PAUSE]

Eine Vollmacht hat keinen Betrag. Ein Energieausweis hat keine Rechnungsnummer. Eine
Flächenberechnung hat beides nicht. Die sind nicht schwer einzuordnen — die sind nach dieser
Regel !!prinzipiell nicht einordenbar!!.

Aber das war nur der zweite Fehler. Der erste war schlimmer.

# Eine Wohnung zu wenig [TIME: 0:00]

Das Werkzeug legt sich vor dem Sortieren ein Profil an: Welche Kategorien gibt es hier, welche
Dokumentarten, was muss belegt sein.

In diesem Profil stand **eine** Wohnung.

Ich habe zwei.

[PAUSE]

Nachgezählt, wie oft die beiden Orte überhaupt in den Dokumenten vorkommen:
**Zweiundsechzig Dateien** betreffen die eine Wohnung. **Sechsundzwanzig** die andere.
Und die Kategorie gab es nur für die **kleinere**.

Die größere hatte kein Zuhause. Fünfzig Dateien sind ersatzweise unter „Finanzierung" gelandet,
dreißig unter „Sonstiges", zwölf bekamen gar keine Kategorie.

[NOTE: Einblendung: 62 vs 26, darunter „Kategorie vorhanden: nur für 26"]

# Die Pointe [TIME: 0:00]

Jetzt die Frage, auf die es ankommt: **Wer hat dieses Profil geschrieben?**

Niemand.

Ein Sprachmodell hat es sich aus einem einzigen Satz zusammengereimt — „ordne meine
Wohnungsunterlagen" — und hat daraus eine Buchhaltungs-Feldliste und eine Wohnung gemacht.
Normalerweise bestätigt ein Mensch dieses Profil, bevor es gilt. Bei mir hat ein Skript es
durchgewinkt, weil es nachts lief und morgens etwas fertig sein sollte.

[PAUSE]

!!Der teuerste Fehler in fünf Wochen war keine Modellwahl. Es war eine Entscheidung, die
niemand getroffen hat!!.

# Was die Korrektur gebracht hat [TIME: 0:00]

[NOTE: ZAHLEN NACHTRAGEN — Gegenversuch lief am 24.09. abends, Ergebnis in
`2026-09-24-praxistest-echter-bestand.md`. Vor der Aufnahme dort abholen; hier steht bewusst
noch keine Zahl, statt eine plausible zu erfinden.]

Vorhergesagt habe ich es vorher, aus den vorhandenen Daten — und die Vorhersage hat meine eigene
Diagnose nach unten korrigiert, bevor sie Rechenzeit gekostet hat: die Pflichtfelder allein retten
nur zwölf von dreiundvierzig Dokumenten, nicht dreiundzwanzig. Weil dieselben Dateien zusätzlich
am Datum oder an der Dokumentart scheitern.

# Und die eine Zahl, die mir Sorgen macht [TIME: 0:00]

Bei **sieben** Fragen hat das System geantwortet, obwohl das richtige Dokument gar nicht im Index
war. Es hat also aus einem **falschen** Dokument geantwortet — selbstbewusst, mit Zitat. In einem
Fall stimmte der Wert zufällig trotzdem.

[PAUSE]

Sechs belegte Falschauskünfte. Das wiegt schwerer als sechsmal „weiß ich nicht", und das ist
offen. Da bin ich noch nicht fertig.

# Was du daraus mitnehmen sollst [TIME: 0:00]

Drei Sätze.

**Erstens:** Eine Zahl aus einem Testkorpus sagt dir, dass dein Werkzeug funktioniert. Sie sagt
dir !!nicht!!, wie gut es auf deinen Unterlagen funktioniert. Bei mir war der Unterschied
neunzig zu sechsundzwanzig.

**Zweitens:** Der Engpass war nicht das Modell, nicht das Embedding, nicht die Suche. Es war die
Frage, ob ein Dokument überhaupt in den Index kommt. Was da hängenbleibt, findest du nie —
egal, wie gut der Rest ist.

**Drittens, und das ist das eigentliche:** Die wichtigste Entscheidung in der ganzen Kette war
eine Konfigurationsdatei. Und ich habe sie eine Maschine treffen lassen, weil ich schlafen wollte.

[PAUSE]

Genau dafür gibt es das Messen. Nicht damit man recht behält — damit man merkt, wenn man
unrecht hat.

---

## Quellen (nicht sprechen)

- Alle Zahlen: `../lokalki-lab/docs/messungen/2026-09-24-praxistest-echter-bestand.md`.
- Rohdaten (privat, außerhalb beider Repos): der Ordner aus `DOKASS_FRAGEN`.
- Vorbehalt zur 90-%-Zahl steht seit 24.09. oben in `modelle.yaml`; der ältere Baustein
  `skript-baustein-entscheidung.md` nennt „159 von 163" — das gilt **nur** für den synthetischen
  Korpus und muss beim Zusammenschnitt entweder eingeordnet oder ersetzt werden.
- Nicht erwähnen, weil unfertig: die Zahlen des Gegenversuchs (siehe NOTE oben) und die
  Ursache der sieben Fremdbeleg-Antworten.
