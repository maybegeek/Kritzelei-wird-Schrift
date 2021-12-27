# *Kritzelei wird Schrift*

Weiterentwicklung von `Hand2Font`.

Von handgekritzelten Zeichen zum weiterbearbeitbaren Font. Drei Blatt mit je 49 Kästchen stehen bereit für die jeweiligen Zeichen. Sind die Kästchen ausgefüllt, können die Bögen per Foto oder Scan umgewandelt werden.

Für die Weiterverarbeitung gibt es ein Skript zum entzerren und zuschneiden der Glyphen-Vorlage. Hernach werden die Kästchen per `opencv` erkannt, der Inhalt der Boxen dann ausgeschnitten und die vorliegenden Einzelbilder der Kästcheninhalte umgewandelt in `*.ppm`-Dateien um diese dann per `potrace` zu vektorisieren. Die erstellten `*.svg`-Dateien werden im nächsten Schritt an vorgesehenen Positionen im `Font` platziert und eine `*.sfd`-Datei erstellt.

Die automatische Umwandlung der Zeichen soll einige Schritte bei der Erstellung einer eigenen Schrift mit `Fontforge` beschleunigen. Es wartet auf jeden Interessierten aber noch genügend (Fein-)Arbeit bei der Verbesserung der automatisch erstellten `*.sfd`-Datei.

## Kritzelei-Zeichenvorlage

![Zeichenvorlage-A](Kritzelei-Zeichenvorlage/Kritzelei-Zeichenvorlage-0.png "Zeichenvorlage-A") ![Zeichenvorlage-B](Kritzelei-Zeichenvorlage/Kritzelei-Zeichenvorlage-1.png "Zeichenvorlage-B") ![Zeichenvorlage-C](Kritzelei-Zeichenvorlage/Kritzelei-Zeichenvorlage-2.png "Zeichenvorlage-C")

## magic

Bei der Erstellung des Fonts werden zu den eigenen Zeichen noch weitere Einstellungen vorgenommen:

* der Zeichensatz festgelegt: `UnicodeFull`
* Versionsnummer für den Font vergeben: `1.0`
* font weight: `Regular`
* `fontname`, `familyname` und `fullname`
* `font.comment = 'FONT_COMMENT'`
* `font.copyright = 'FONT_LICENSE'`
* em-size: `2048`
* Layers: `cubic`
* `stylistic sets`
* `liga`, normale Ligaturen
* `dlig`, discretionary ligatures
* besondere Leerzeichen
* Katzenpfoten!
* `.notdef`-Quisquilie
* side bearings
* Größenanpassung ... automagisch
* Grundlinien- x-Höhen-Anpassung


## Nutzung

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


`-t 160`: Schwellwert hinsichtlich der Umwandlung (Kastenerkennung). Zwischen 0 und 255, wobei ich für den Standard ca. um die 160 vorschlagen würde.

`-o Ordner`: Ordnername und Ziel, in welchem die Dateien abgelegt werden.

`-n KritzeleiFont`: Wie soll der Font später heißen?

`--rmppm`: *.ppm-Dateien im Erstellungsordner entfernen.

`--rmjpg`: *.jpg-Dateien im Erstellungsordner entfernen.

`--rmsvg`: *.svg-Dateien im Erstellungsordner entfernen.

`--buntstift`: bei Buntstift, Farbe, uneinheitlicher Deckkraft, ... (resultiert in Verwendung von `--blacklevel 0.96`)

Viel Vergnügen
