# Retrieval-Eval — beweise/germanquad, Stufe 474

| Variante | Embedding | Fundstellen | Embed s | Recall@1 | Recall@3 | Recall@5 | Recall@8 | Recall@12 | Recall@20 | MRR | Nicht-gefunden-Quote % | Dauer/Frage s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | – | 474 | – | 83 | 92 | 94 | 96 | 96 | 98 | 0.876 | – | 0.026 |
| bm25_komposita | – | 474 | – | 83 | 91 | 94 | 96 | 96 | 98 | 0.878 | – | 0.026 |
| bm25_praefix | – | 474 | – | 86 | 94 | 97 | 98 | 98 | 99 | 0.905 | – | 0.050 |
| dense | bge-m3 | 474 | 48.0 | 91 | 98 | 98 | 99 | 100 | 100 | 0.946 | – | 0.083 |
| dense | qwen3-embedding:0.6b | 474 | 86.1 | 82 | 95 | 95 | 97 | 98 | 98 | 0.879 | – | 0.062 |
| hybrid | bge-m3 | 474 | 48.0 | 88 | 96 | 99 | 100 | 100 | 100 | 0.924 | – | 0.083 |
| hybrid | qwen3-embedding:0.6b | 474 | 86.1 | 83 | 95 | 98 | 100 | 100 | 100 | 0.892 | – | 0.062 |
| hybrid_komposita_w0.5 | bge-m3 | 474 | 48.0 | 92 | 98 | 99 | 100 | 100 | 100 | 0.948 | – | 0.083 |
| hybrid_komposita_w0.5 | qwen3-embedding:0.6b | 474 | 86.1 | 86 | 96 | 98 | 98 | 100 | 100 | 0.91 | – | 0.062 |
| hybrid_komposita_w1.0 | bge-m3 | 474 | 48.0 | 88 | 96 | 98 | 100 | 100 | 100 | 0.927 | – | 0.083 |
| hybrid_komposita_w1.0 | qwen3-embedding:0.6b | 474 | 86.1 | 85 | 96 | 97 | 100 | 100 | 100 | 0.905 | – | 0.062 |
| hybrid_w0.25 | bge-m3 | 474 | 48.0 | 91 | 98 | 100 | 100 | 100 | 100 | 0.947 | – | 0.083 |
| hybrid_w0.25 | qwen3-embedding:0.6b | 474 | 86.1 | 86 | 96 | 97 | 98 | 98 | 100 | 0.912 | – | 0.062 |
| hybrid_w0.5 | bge-m3 | 474 | 48.0 | 92 | 98 | 100 | 100 | 100 | 100 | 0.949 | – | 0.083 |
| hybrid_w0.5 | qwen3-embedding:0.6b | 474 | 86.1 | 86 | 96 | 98 | 98 | 100 | 100 | 0.91 | – | 0.062 |

## Absatzgenau

Treffer = genau der Zielabsatz (`absatz_id`), nicht nur die richtige Datei.

| Variante | Embedding | Recall@1 | Recall@3 | Recall@5 | Recall@8 | Recall@12 | Recall@20 | MRR |
|---|---|---|---|---|---|---|---|---|
| bm25 | – | 83 | 92 | 94 | 96 | 96 | 98 | 0.876 |
| bm25_komposita | – | 83 | 91 | 94 | 96 | 96 | 98 | 0.878 |
| bm25_praefix | – | 86 | 94 | 97 | 98 | 98 | 99 | 0.905 |
| dense | bge-m3 | 91 | 98 | 98 | 99 | 100 | 100 | 0.946 |
| dense | qwen3-embedding:0.6b | 82 | 95 | 95 | 97 | 98 | 98 | 0.879 |
| hybrid | bge-m3 | 88 | 96 | 99 | 100 | 100 | 100 | 0.924 |
| hybrid | qwen3-embedding:0.6b | 83 | 95 | 98 | 100 | 100 | 100 | 0.892 |
| hybrid_komposita_w0.5 | bge-m3 | 92 | 98 | 99 | 100 | 100 | 100 | 0.948 |
| hybrid_komposita_w0.5 | qwen3-embedding:0.6b | 86 | 96 | 98 | 98 | 100 | 100 | 0.91 |
| hybrid_komposita_w1.0 | bge-m3 | 88 | 96 | 98 | 100 | 100 | 100 | 0.927 |
| hybrid_komposita_w1.0 | qwen3-embedding:0.6b | 85 | 96 | 97 | 100 | 100 | 100 | 0.905 |
| hybrid_w0.25 | bge-m3 | 91 | 98 | 100 | 100 | 100 | 100 | 0.947 |
| hybrid_w0.25 | qwen3-embedding:0.6b | 86 | 96 | 97 | 98 | 98 | 100 | 0.912 |
| hybrid_w0.5 | bge-m3 | 92 | 98 | 100 | 100 | 100 | 100 | 0.949 |
| hybrid_w0.5 | qwen3-embedding:0.6b | 86 | 96 | 98 | 98 | 100 | 100 | 0.91 |

## Wo es bricht

| Frage | bm25@- | bm25_komposita@- | bm25_praefix@- | dense@bge-m3 | dense@qwen3-embedding:0.6b | hybrid@bge-m3 | hybrid@qwen3-embedding:0.6b | hybrid_komposita_w0.5@bge-m3 | hybrid_komposita_w0.5@qwen3-embedding:0.6b | hybrid_komposita_w1.0@bge-m3 | hybrid_komposita_w1.0@qwen3-embedding:0.6b | hybrid_w0.25@bge-m3 | hybrid_w0.25@qwen3-embedding:0.6b | hybrid_w0.5@bge-m3 | hybrid_w0.5@qwen3-embedding:0.6b |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wo wurde ein seilloser Aufzug entwickelt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was ist das Hauptziel von Softwaretest? | 3 | 1 | 1 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo spielte der FC Barcelona bei dessen Gründung? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was war die erste Spielstätte des FC Barcelona? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo leben die meisten schwarzen in Frankreich? | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo hat Subhash Chandra Bose die Indische Nationale Armee gegründet? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Warum ist öffentliche Verkehrsmittel so beliebt in New York? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie ist das Zehrgebiet des Gletschers definiert? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann wurde der Hatt-i Hümayun erlassen? | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viele Steuerzeichen gibt es im ASCII-Code? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Armeen der Welt haben mehr Mann als die US-Army? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Woran grenzt Zhejiang im Norden? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Woran grenzt Zhejiang im Osten? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann kommen die meisten Touristen nach Bern? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was war die kälteste gemessene Temperatur in Oklahoma City? | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 2 | 1 |
| Welche Maßnahmen unternimmt die Türkei gegen Zypern? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wieso reiste Queen Victorias Mann kurz vor seinem Tod nach Cambridge? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Durch was wird das Hochskalieren bei neueren HDTV-Auflösungen begünstigt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was ist die Übertragungsrate von USB 3.0? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Ab wann war in englischen Pubs nach 1915 Sperrstunde? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| An welcher Krankheit litt Queen Victoria zur Zeit ihres 60. Regierunsjubiläums? | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 2 | 1 |
| Welches Gebäude in Oklahoma wurde 1995 durch einen Bombenanschlag zerstört? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was strebte die indianische Bevölkerung in Oklahoma Anfang des 20. Jhd. an? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viele Menschen starben bei dem Anschlag 1993 auf das World Trade Center? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer entwarf die Gedenkstätte für die Opfer des 11. September? | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo wurde die Sozialdemokratische Arbeiterpartei gegründet? | 1 | 5 | 3 | 5 | 35 | 1 | 3 | 3 | 9 | 3 | 8 | 1 | 17 | 1 | 4 |
| Was war ein Spitzname für Herzog Ernst II. von Sachsen-Coburg? | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer lud zum sogenannten Wartburgfest ein? | 13 | 13 | 13 | 2 | 27 | 1 | 7 | 1 | 11 | 1 | 7 | 1 | 13 | 1 | 11 |
| Ab wann gab es die erste Zugstrecke in Thüringen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Müssen Hunde gegen Tollwut geimpft werden? | 5 | 5 | 1 | 1 | 1 | 4 | 3 | 1 | 1 | 4 | 3 | 1 | 1 | 1 | 1 |
| Warum unterstütze al-Gaddafi die IRA? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was sind Verbrechen gegen die Menschlichkeit? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Bei welchen Körpern zeigen sich unterschiedliche WIrkungen bei gleichem Impuls? | 1 | 1 | 1 | 4 | 9 | 1 | 2 | 1 | 2 | 1 | 2 | 2 | 2 | 1 | 2 |
| Was behandelt eine bekannte Veröffentlichung von Carnot von 1824? | 1 | 1 | 1 | 2 | 3 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 2 |
| Wann wurde Israel gegründet? | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 1 | 2 | 1 |
| Wie war der bürgerliche Name von Thayendanegea? | 1 | 1 | 1 | 9 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 |
| Wann ist in Mexiko City Regenzeit? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| In welchem Monat gibt es in Mexico City durchschnittlich die höchsten Temperaturen? | 2 | 2 | 8 | 1 | 1 | 2 | 2 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 |
| Wo spielt "Wer die Nachtigall stört"? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer ist die Erzählerin von "Wer die Nachtigall stört"? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was wird Tom Robinson in Wer die Nachtigall stört vorgeworfen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was geschieht am Ende des Romans Wer die Nachtigall stört mit Robinson? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Städte außerhalb Kanada sind von dem St. John's International Airport erreichbar? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viel Prozent der Stimmen hat der Vorgänger von Miguel Angel Mancera bei den Wahlen bekommen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer war der Vorgänger von Marcelo Ebrard? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann reiste Menschikow aus dem Osmanischen Reich ab, nachdem seine Mission gescheitert ist? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was bedeutet "nachhaltiger Föderalismus"? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viel wiegt das Gehirn eines Mannes durchschnittlich? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was ist der Unterschied zwischen einer Amygdala eines Mannes und einer Frau? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie kann man den Unterschied in den beiden Hirnhemisphären von Männern und Frauen erklären? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| In welchem Bundesstaat ist die Northwestern University angesiedelt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie hat sich die Literatur in Tibet mit der Annexion des Landes durch China verändert?  | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie wird die Zugfestigkeit von Papier gemessen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie wird der Berstwiderstand beim Papier gemessen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| In wie viele Teile wird San Diego geteilt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was beendete den Österreichischen Erbfolgekrieg? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Warum werden Schutzringkondensatoren gebaut? | 3 | 3 | 11 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Als was bezeichnen die Demokraten bei Wahlen die im Ausland lebenden Wähler? | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie heißt das erste Werk von Whitehead im Bereich Naturphilosophie? | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie sind Daten auf Laserdiscs gespeichert? | 3 | 3 | 3 | 1 | 1 | 2 | 2 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 |
| Wie tritt Zink im Blutkreislauf auf? | 3 | 1 | 3 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was sind die Folgen von zu viel Zink? | 3 | 3 | 3 | 1 | 1 | 2 | 2 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 |
| Wer verwaltet die Unis in Deutschland? | 28 | 61 | 35 | 1 | 1 | 4 | 6 | 6 | 7 | 8 | 7 | 2 | 2 | 4 | 4 |
| Was ist die Fundstelle Neumark-Nord? | 1 | 1 | 1 | 1 | 57 | 1 | 4 | 1 | 11 | 1 | 2 | 1 | 30 | 1 | 10 |
| Welche Eigenschaft des Menschen wurde durch den Übergang von Fell zu Haut begünstigt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer prägte den Begriff Wirkungsquantum? | 4 | 4 | 4 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| Was ist Spin von teilchen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo hat der Europäische Gerichtshof für Menschenrechte seinen SItz? | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 |
| Wieso nahm Holland in den Vereinigten Provinzen eine Vormachtsstellung ein? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was heißt Conca d'Oro? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann schlossen Ägypten und Israel einen Friedensvertrag? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann wurde die christliche Religion zur Staatsreligion im Römischen Reich? | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Als was wollte Stalin laut Sergej Slutsch die Verhandlungen mit den Westmächten nutzen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Durch was sah Stalin laut Historikern die Sowjetunion vor dem 2. Weltkrieg  umgeben? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was war laut MIcheal Carley der ideologische Antrieb der Politik von England und Frankreich vor dem 2. Weltkrieg? | 8 | 6 | 3 | 10 | 8 | 5 | 3 | 4 | 3 | 3 | 2 | 5 | 5 | 3 | 3 |
| Welches Studio kaufte DreamWorks? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Zeitung schrieb im Vorfeld des Moratoriums der Todesstrafe in Illinois über Probleme in der Justiz? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Seit wann werden US-Dollarnoten mit Sicherheitsaufdrucken versehen? | 16 | 2 | 1 | 1 | 1 | 4 | 3 | 1 | 1 | 2 | 2 | 3 | 3 | 3 | 3 |
| Wie werden Wasserzeichen erzeugt? | 1 | 1 | 6 | 2 | 3 | 1 | 2 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 2 |
| Welche Bedeutung hatte das Jagen ab etwa 6500 v.Chr.? | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Aus welcher Epoche stammt das erste nachgewiesene kultivierte Getreide? | 28 | 28 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 2 |
| Was bezeichnet in Mitteleuropa die Kupferzeit? | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welchen Zweig der Physik etablierte Planck mit der Entdeckung des Wirkungsquantums? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann starb Alexander der Große? | 4 | 4 | 2 | 8 | 6 | 2 | 3 | 2 | 3 | 2 | 3 | 4 | 3 | 2 | 3 |
| Wann wurde Ägypten Teil des römischen Reiches? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer war der letzte Nachfahre des ptolemäischen Herrscherfamilie, der in Ägypten regierte? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Nach welchem Konzil entstand die koptische Kirche? | 1 | 1 | 1 | 1 | 6 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 2 |
| Wofür wurde Queen Elisabeth II. 1987 in Kanada kritisiert? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was ist der HLA-Komplex? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Zu welcher Unterteilung der Immunreaktion führten u.a. die Ergebnisse von Jacques Miller? | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie kann Zink nachgewiesen werden? | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was entsteht beim Zinknachweis mit Cobaltsalzlösung? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Für welche Partei kandidierte John McCain 2008 als Präsident? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Stoffe werden bei der Herstellung von Bier zugesetzt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was wird bei der Herstellung von Wein und Bier gegärt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann brechen persistierende Infektionen wieder aus? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Bei welcher Art von Infektion kann der Erreger nicht nachgewiesen werden? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann wurde die CIA gegründet? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Der Versuch eines Attentats 1995 im Hauptquartier der CIA hatte was als Folge?  | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer wurde 2018 zum neuen Außenminister der USA ernannt?  | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer ist derzeit der CIA-Chef? | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 3 | 1 | 3 |
| Wo haben sich Denker in der Zeit der Aufklärung getroffen? | 14 | 14 | 5 | 1 | 1 | 5 | 5 | 3 | 4 | 5 | 5 | 3 | 3 | 3 | 4 |
| Welche Frauen waren aktiv während der Frühaufklärung in Deutschland? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie sehen Eier von Ursäugern aus? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo hat die WWE die Wrestling-Industrie expandiert? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann ist die Krönung von Victoria stattgefunden? | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 2 |
| Wann besiegte die ägyptische Armee die osmanische in der Schlacht von Nisibis? | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was wurde in Ägypten im 19.Jahrhundert angebaut, das für Europa interessant war? | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 1 |
| Wie sehen die Böden der atlantischen Küstenebene von North Carolina? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wofür kann man die Böden der atlantischen Küstenebene von North Carolina verwenden? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was ist "Outer Banks" in North Carolina? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was ist die geologische Struktur der Piedmont-Region von North Carolina? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| In welchem Teil von North Carolina werden heutzutage verschiedene Baumaterialen abgebaut? | 2 | 2 | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 |
| Was bildet die Westgrenze von North Carolina? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie nennt man den Verzehr von Insekten? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was beinhaltet das Hauptwerk von Edmund Burke? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Warum kam es zu so vielen Toten nach dem Erdbeben 1985 in Mexiko-Stadt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie sieht die Landschaft der Mexiko-Stadt aus? | 6 | 6 | 1 | 1 | 3 | 2 | 4 | 1 | 4 | 2 | 4 | 1 | 4 | 1 | 4 |
| Was wird in der Mexiko-Stadt angebaut? | 6 | 6 | 5 | 2 | 2 | 4 | 4 | 2 | 2 | 4 | 4 | 2 | 2 | 2 | 2 |
| Wie lang ist die Straßenbahnstrecke in Mexiko-Stadt heutzutage? | 3 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Sportveranstaltung findet häufig in Miami statt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Seit wann gibt es den Begriff des religiösen oder spirituellen Naturalismus? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was ist das größte Blasmusikfestival der Welt? | 1 | 1 | 1 | 1 | 24 | 1 | 2 | 1 | 2 | 1 | 2 | 1 | 7 | 1 | 2 |
| Mit welchen Päpsten hat sich Elisabeth II getroffen? | 2 | 2 | 1 | 3 | 3 | 2 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 3 |
| Was bedeutet ein Umformer, der zum Leistungsausgleich eingesetzt wird? | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 2 | 1 |
| Nach wem wurde die "Kaiser-Wilhelm- Universität" in Straußburg benannt? | 3 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Dimensionen zählen für NPOs im Bereich der sozialen Arbeit? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was spricht laut der Philosophie in der Tradition von Platon und Aristoteles für die Immaterialität Gottes? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo fand die Operation TA der Japaner statt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Woher bekam Arnold Schwarzenegger Anfangs sein Wissen über das Bodybuilding? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo spielen die Detroit Red Wings heutzutage? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wan war Elisabeth II. das erste mal im "Time" Magazin auf der Titelseite? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viel verdient der Durchschnittliche Haushalt in Seattle? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Bakterien sterben von Sauerstoff? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo liegt der Der Élysée-Palast? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie ist Griechenlands Energiehandelsbilanz? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was ist das Monumento a los Niños Héroes? | 1 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie hoch lieg der Ort Säntis? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer wurde 1968 Präsident des FC Barcelona? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was gab der FC Barcelona der Bevölkerung Kataloniens zur Zeit Francos? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welches Amt hatte Josip Broz Tito bis er starb? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viele der Kinder Nigerias im Schulalter gehen zur Schule? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo hat die US Army Rekrutierungsstellen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann bekam ein Asteroid Feynmans Namen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Auszeichnung bekam Richard Feynman 1954? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Einstellung hatte Hans Blüher gegenüber der humanistischen Bildung? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Länder sind ein Teil von Südostasien? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann waren die ersten Spiele der Zweitmannschaft vom FC Everton? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer darf in den Deutschland den Titel Universität besitzen? | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 2 |
| Zu welchem Land gehört die Provinz Berg-Badachschan? | 1 | 1 | 1 | 1 | 6 | 1 | 2 | 1 | 2 | 1 | 2 | 1 | 3 | 1 | 2 |
| Wie heißen Valencias Universitäten? | 6 | 6 | 1 | 1 | 1 | 3 | 3 | 3 | 3 | 3 | 3 | 1 | 1 | 3 | 3 |
| Zu welchem Sprachtyp gehört Russisch? | 188 | 188 | 2 | 1 | 1 | 3 | 8 | 2 | 3 | 3 | 8 | 2 | 2 | 2 | 3 |
| Wie viele Zeit Typen hat die deutsche Sprache? | 26 | 26 | 4 | 1 | 1 | 6 | 7 | 5 | 4 | 6 | 7 | 5 | 3 | 5 | 4 |
| Seit wann gibt es die Option eine Ausbildung in Teilzeit zu machen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Woher kommt der Reis Bomba? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer wurde nach Ed Rendell Gouverneur Pennsylvanias? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Währungen sind Teil des Vergleich Korbes des USDX | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo steht der Schiedsrichter beim Canadian Football vor dem Snap? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Warum brauchten die Amerikaner eine eigene See Armee? | 121 | 121 | 149 | 2 | 3 | 20 | 20 | 11 | 11 | 20 | 20 | 5 | 7 | 11 | 11 |
| Wer war 1785 der US-Botschafter in Frankreich? | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viel kosteten die Tribut- und Lösegeldzahlungen die USA 1800? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Über welche Schiffe hatte Edward Prieble den Oberbefehl im ersten Barbareskenkrieg? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann war die Schlacht von Derna? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Womit kann man bei der "Xbox Live Arcade" spiele kaufen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viele Truppen hatten die Deutschen insgesamt im Deutsch Französischen Krieg? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welches Land kolonialisierte Eritrea? | 4 | 4 | 3 | 1 | 1 | 3 | 3 | 1 | 1 | 3 | 3 | 1 | 1 | 1 | 1 |
| Wo leben deutschstämmige in Tadschikistan heutzutage größteils? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was sind Orphan-Gene? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Gebiete in North Carolina wurden von den schottisch-irischen und nord-englischen Einwanderern besiedelt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| An welchem Ort von North Carolina haben sich die Hugenotten und Deutschschweizer niedergelassen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann haben die Kolonien Senegal und Französisch- Sudan ihre Unabhängigkeit als Mali- Föderation bekommen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Warum hatten andere Menschen Angst vor von Neumann? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Inwiefern hat von Neumann bei dem Abwurf der Atombomben auf Japan mitgemacht? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welches Gebiet beanspruchte Frankreich 1866? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Durch welches Zusammentreffen wurde die Luxemburgkrise  beendet? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Staaten führten die Suez-Kampagne? | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was war der Plan der Suez-Kampagne? | 3 | 3 | 3 | 2 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viele Einwohner hat die Stadt Naucalpán? | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Ziele verfolgt die iranische Außenpolitik seit der islamischen Revolution? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer ist 2005 die Ehefrau von Ross Kemp? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie sieht die Flamme von Wasserstoff aus? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Sprache wurde ursprünglich für die Schriften  des Mahayana-Buddhismus verwendet? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viele Kinder hatte Gamal Abdel Nasser? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wer gab Israel Informationen über den Überraschungsangriff geplanten Jom-Kippur-Krieg? | 1 | 1 | 1 | 1 | 14 | 1 | 5 | 1 | 5 | 1 | 3 | 1 | 8 | 1 | 6 |
| Wie stark wächst Estlands BIP seit dem Jahr 2000? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was sind die Folgen einer fehlenden Zeitumstellung? | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie werden Entscheidungsfragen im Estnischen gebildet? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann wird beim FA Cup ein Rückspiel gespielt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Platzierung erreichte Beyonces Album "4" in den Billboard 200? | 2 | 2 | 2 | 1 | 1 | 2 | 2 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 |
| Was trennt die USA und Russland geographisch? | 1 | 5 | 4 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo kommt ein drittel des deutschen Bahnstroms 2018 her? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was ist die wichtigste Wirtschaft der Norfolkinsel? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie heißt das philosophische Hauptwerk von Whitehead? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wozu dient der Schleim der Nebenzellen im Magen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo in der Schweiz wird Fronleichnam gefeiert? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche iPod-Generation wird  classic genannt? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie viele natürliche Isotope des Wasserstoffs gibt es? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wo kann man das dritte Isotop des Wasserstoffs finden? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Seit wann leben in Indien menschliche Kulturen? | 12 | 12 | 1 | 1 | 1 | 4 | 2 | 1 | 2 | 4 | 2 | 1 | 1 | 1 | 2 |
| In welchem Teil Indies entstand das tamilische Chola-Reich? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
