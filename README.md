# Kritzelei-wird-Schrift

Weiterentwicklung von `Hand2Font`.


# vorläufige Dokumentation

Als Pandemie-Überarbeitung wurde mehr auf die mobile Nutzung abgestellt, Smartphone-Fotos liegen deshalb im Fokus. Downsamplen von großen Scans könnten mögliche Probleme beseitigen.

In den Ordner `Kritzelei-Bilder-Original` kommen die Fotos der ausgefüllten `Kritzelei-Zeichenvorlage`.

Möglicher Inhalt dort:

* `Kritzelei-Bilder-Original/A-orig.jpg`
* `Kritzelei-Bilder-Original/B-orig.jpg`
* `Kritzelei-Bilder-Original/C-orig.jpg`

Mittels `python3 Kritzelei-Bilder-Vorbereitung.py` -- uns bisher fester Eingabe der Quell- und Zieldatei darin wird in den Ordner (Vorschlag) `Kritzelei-Bilder-Vorbereitung` das Bildmaterial beschnitten und entzerrt.

Möglicher Inhalt dort:

* `Kritzelei-Bilder-Vorbereitung/A.jpg`
* `Kritzelei-Bilder-Vorbereitung/B.jpg`
* `Kritzelei-Bilder-Vorbereitung/C.jpg`

Wollen wir nachsehen, ob die Glyphen in den jeweiligen Kästen ordentlich und in ordentlicher Reihenfolge erkannt werden -- das ist ja durchaus sehr wichtig für den nächsten Schritt -- so können wir dies mit `python3 Kritzelei-Bilder-Fehlersuche.py -s Kritzelei-Bilder-Vorbereitung` tun.

Hier werden uns dann in einem kleinen Fenster die Originaldatei und das Erkannte angezeigt. Mit `ESC` können wir die kleinen Darstellungen jeweils Bestätigen und so Durchschalten.

Passt dies, geht es weiter. Grundlegend hier zwei Aufrufe, weitere Einstellmöglichkeiten kann man vorerst der Hilfe innerhalb des Skripts entnehmen, oder bei Durchsicht des Skripts selbst sehen und ändern:

Hier also die vorbereiteten Bilder aus `Kritzelei-Bilder-Vorbereitung` holen (A,B,C) und in den Ordner `Output/Kritzelei-01` mit Schriftnamen `Kritzelei-01` hinein die Glyphenbilder, deren Umwandlung und eine weiterverwendbare `.sfd` erzeugen. Schwellwerte für Strichdicke, Unreinheiten usw. könnten ebenfalls noch verwendet werden. `--rmppm`, `--rmsvg` oder `--rmjpg` entfernt nämliche Zwischenschrittdateien.

`python3 Kritzelei-wird-Schrift-Scan2SVG.py --scans Kritzelei-Bilder-Vorbereitung/ -o Output/Kritzelei-01 -n Kritzelei-01 --rmppm`


Ein bisschen mit den Optionen wird man schon spielen müssen, hier eine Variante, welche gerade bei bestimmten Stiftverwendungen und Stiftfarbenverwendungen erfolgreich war:


`python3 Kritzelei-wird-Schrift-Scan2SVG.py --scans Kritzelei-Bilder-Vorbereitung/ -o Output/Kritzelei-02 -n Kritzelei-02 --rmppm --buntstift`

Viel Vergnügen
