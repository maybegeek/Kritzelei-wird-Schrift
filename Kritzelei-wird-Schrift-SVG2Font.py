#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import vorliegender SVG-Dateien und Erstellung einer Font-Datei."""

import os
import sys
import math
import glob
import psMat
import fontforge
import tempfile
import argparse

__author__ = "Christoph Pfeiffer"
__license__ = "CC-BY-NC-SA-4.0"

ap = argparse.ArgumentParser(
    description = 'Import der SVG-Dateien in FontForge ... + magic.'
)

ap.add_argument(
    '-svg'
    , '--svgordner'
    , help = 'Ordner der SVG-Dateien.'
    , type = str
    , required = True
)

ap.add_argument(
    "-n"
    , "--name"
    , help = "Name der Schrift."
    , required = True
    , type = str
)

ap.add_argument(
    "-v"
    , "--version"
    , help = "Version des Eingabebogens."
    , required = True
    , type = int
)

args = ap.parse_args()

pfad = args.svgordner
pfad = pfad.rstrip('/') + '/'
name = args.name
version = args.version

glyphsSVG = [f for f in glob.glob(pfad + "*.svg")]
glyphsSVG.sort()

# Reihenfolge der Glyphen.
# Für die unterschiedlichen Versionen der Erfassungsbögen
if version == 1:
  glyphsUTF8 = [['A', 65], ['B', 66], ['C', 67], ['D', 68], ['E', 69], ['F', 70], ['G', 71], ['H', 72], ['I', 73], ['J', 74], ['K', 75], ['L', 76], ['M', 77], ['N', 78], ['O', 79], ['P', 80], ['Q', 81], ['R', 82], ['S', 83], ['T', 84], ['U', 85], ['V', 86], ['W', 87], ['X', 88], ['Y', 89], ['Z', 90], ['Ä', 196], ['Ö', 214], ['Ü', 220], ['ẞ', 7838], ['a', 97], ['b', 98], ['c', 99], ['d', 100], ['e', 101], ['f', 102], ['g', 103], ['h', 104], ['i', 105], ['j', 106], ['k', 107], ['l', 108], ['m', 109], ['n', 110], ['o', 111], ['p', 112], ['q', 113], ['r', 114], ['s', 115], ['t', 116], ['u', 117], ['v', 118], ['w', 119], ['x', 120], ['y', 121], ['z', 122], ['ä', 228], ['ö', 246], ['ü', 252], ['ß', 223], ['1', 49], ['2', 50], ['3', 51], ['4', 52], ['5', 53], ['6', 54], ['7', 55], ['8', 56], ['9', 57], ['0', 48], ['!', 33], ['?', 63], ['§', 167], ['$', 36], ['%', 37], ['&', 38], ['/', 47], ['(', 40], [')', 41], ['{', 123], ['}', 125], ['[', 91], [']', 93], ['=', 61], ['<', 60], ['>', 62], ['|', 124], ['\\', 92], [',', 44], [';', 59], ['*', 42], ['.', 46], [':', 58], ['-', 45], ['–', 8211], ['#', 35], ['+', 43], ['~', 126], ['"', 34], ["'", 39], ['@', 64], ['^', 94], ['_', 95], ['`', 96], ['·', 183], ['«', 171], ['»', 187], ['¼', 188], ['½', 189], ['¾', 190], ['‚', 8218], ['‘', 8216], ['„', 8222], ['“', 8220], ['…', 8230], ['€', 8364], ['ﬀ', 64256], ['ﬁ', 64257], ['ﬂ', 64258], ['ﬃ', 64259], ['c_k.liga', 993082], ['Q_u.liga', 993083], ['s_s.liga', 993084], ['e_i.liga', 993085], ['t_t.liga', 993086], ['a.ss01', 993070], ['a.ss02', 993071], ['d.ss01', 993072], ['e.ss01', 993073], ['e.ss02', 993074], ['i.ss01', 993075], ['m.ss01', 993076], ['n.ss01', 993077], ['o.ss01', 993078], ['r.ss01', 993079], ['s.ss01', 993080], ['t.ss01', 993081]]
elif version == 2:
  glyphsUTF8 = [['A', 65], ['B', 66], ['C', 67], ['D', 68], ['E', 69], ['F', 70], ['G', 71], ['H', 72], ['I', 73], ['J', 74], ['K', 75], ['L', 76], ['M', 77], ['N', 78], ['O', 79], ['P', 80], ['Q', 81], ['R', 82], ['S', 83], ['T', 84], ['U', 85], ['V', 86], ['W', 87], ['X', 88], ['Y', 89], ['Z', 90], ['Ä', 196], ['Ö', 214], ['Ü', 220], ['ẞ', 7838], ['a', 97], ['b', 98], ['c', 99], ['d', 100], ['e', 101], ['f', 102], ['g', 103], ['h', 104], ['i', 105], ['j', 106], ['k', 107], ['l', 108], ['m', 109], ['n', 110], ['o', 111], ['p', 112], ['q', 113], ['r', 114], ['s', 115], ['t', 116], ['u', 117], ['v', 118], ['w', 119], ['x', 120], ['y', 121], ['z', 122], ['ä', 228], ['ö', 246], ['ü', 252], ['ß', 223], ['1', 49], ['2', 50], ['3', 51], ['4', 52], ['5', 53], ['6', 54], ['7', 55], ['8', 56], ['9', 57], ['0', 48], ['!', 33], ['?', 63], ['§', 167], ['$', 36], ['%', 37], ['&', 38], ['/', 47], ['(', 40], [')', 41], ['{', 123], ['}', 125], ['[', 91], [']', 93], ['=', 61], ['<', 60], ['>', 62], ['|', 124], ['\\', 92], [',', 44], [';', 59], ['*', 42], ['.', 46], [':', 58], ['-', 45], ['–', 8211], ['#', 35], ['+', 43], ['~', 126], ['"', 34], ["'", 39], ['@', 64], ['^', 94], ['_', 95], ['`', 96], ['·', 183], ['«', 171], ['»', 187], ['¼', 188], ['½', 189], ['¾', 190], ['‚', 8218], ['‘', 8216], ['„', 8222], ['“', 8220], ['…', 8230], ['€', 8364], ['ﬀ', 64256], ['ﬁ', 64257], ['ﬂ', 64258], ['ﬃ', 64259], ['c_k.liga', 993082], ['Q_u.liga', 993083], ['s_s.liga', 993084], ['e_i.liga', 993085], ['t_t.liga', 993086], ['a.ss01', 993070], ['a.ss02', 993071], ['d.ss01', 993072], ['e.ss01', 993073], ['e.ss02', 993074], ['i.ss01', 993075], ['m.ss01', 993076], ['n.ss01', 993077], ['o.ss01', 993078], ['r.ss01', 993079], ['s.ss01', 993080], ['t.ss01', 993081], ['copyright', 0xa9], ['registered', 0xae], ['logicalnot', 0xac], ['paragraph', 0xb6], ['divide', 0xf7], ['multiply', 0xd7], ['uni203d', 0x203d], ['arrowright', 0x2192], ['arrowleft', 0x2190], ['long', 0x17f]]

# grobe Überprüfung, ob soviele SVG-Dateien da sind,
# wie im Font platziert werden sollen.
if len(glyphsSVG) == len(glyphsUTF8):
    print('könnte passen ... los gehts!')
elif len(glyphsSVG) != len(glyphsUTF8):
    print('ungleiche Ausgangslage!')
    exit()

# Font-Erstellung + einige Einstellungen.
font = fontforge.font()
font.encoding = 'UnicodeFull'
font.version = '1.0'
font.weight = 'Regular'
font.fontname = name + '-Regular'
font.familyname = name
font.fullname = name + ' Regular'

font.comment = 'FONT_COMMENT'
font.copyright = 'FONT_LICENSE'

font.em = 2048

font.layers[0].is_quadratic = 0
font.layers[1].is_quadratic = 0

font.addLookup('"ss01" Style Set 1 lookup', 'gsub_single', 1, [['ss01', [['latn', ['dflt']],]],],)
font.addLookupSubtable('"ss01" Style Set 1 lookup', 'ss01')

font.addLookup('"ss02" Style Set 2 lookup', 'gsub_single', (), [['ss02', [['latn', ['dflt']]]]])
font.addLookupSubtable('"ss02" Style Set 2 lookup', 'ss02')

font.addLookup('ligatures', 'gsub_ligature', (), [['liga', [['latn', ['dflt']]]]])
font.addLookupSubtable('ligatures', 'liga')

font.addLookup('extra-ligatures', 'gsub_ligature', (), [['dlig', [['latn', ['dflt']]]]])
font.addLookupSubtable('extra-ligatures', 'dlig')


# weitere ausprobieren
# https://github.com/fontforge/fontforge/issues/2988

# Ein paar Leerzeichen.
# NUL, Default Character
char = font.createChar( 0x0 )
char.width = 390
# C0 Control Character
char = font.createChar( 0xd, 'CR' )
char.width = 390
# Space
char = font.createChar( 0x20, 'space' )
char.width = 390
# NO-Break Space
char = font.createChar( 0xa0, 'uni00A0' )
char.width = 390
# EN Quad
char = font.createChar( 0x2000, 'uni2000' )
char.width = 500
# EM Quad
char = font.createChar( 0x2001, 'uni2001' )
char.width = 900
# EN Space
char = font.createChar( 0x2002, 'uni2002' )
char.width = 500
# EM Space
char = font.createChar( 0x2003, 'uni2003' )
char.width = 900
# Figure Space
char = font.createChar( 0x2007, 'uni2007' )
char.width = 1000
# Punctuation Space
char = font.createChar( 0x2008, 'uni2008' )
char.width = 280
# Thin Space
char = font.createChar( 0x2009, 'uni2009' )
char.width = 200
# Hair Space
char = font.createChar( 0x200a, 'uni200A' )
char.width = 100
# Zero Width Space
char = font.createChar( 0x200b, 'uni200B' )
char.width = 10
# Narrow NO-Break Space
char = font.createChar( 0x202f, 'uni202F' )
char.width = 200

# Glyphen platzieren
for i, f in enumerate(glyphsSVG):
    if glyphsUTF8[i][1] < 993000:
        char = font.createChar( glyphsUTF8[i][1] )
    elif glyphsUTF8[i][1] > 993000:
        char = font.createChar( glyphsUTF8[i][1], glyphsUTF8[i][0] )
    char.importOutlines(f)
    char.simplify()
    char.left_side_bearing = char.right_side_bearing = 48
    char.round()
    char.addExtrema()

# Konturen der Katzenpfoten ... und damit eine Möglichkeit
# des Einbettens von Zeicheninformationen im Skript
contour01 = [[5300.34, 1036.19], [5320.85, 1019.84, 5347.91, 992.853, 5338.59, 953.574], [5325.98, 900.205, 5264.84, 868.537, 5193.96, 870.44], [5133.45, 872.166, 5081.55, 897.599, 5055.28, 938.638], [5026.91, 983.048, 5057.27, 1029.44, 5092.14, 1050.5], [5153.45, 1087.86, 5250.42, 1076.07, 5300.34, 1036.19]]
contour02 = [[5195.38, 1327.65], [5255.78, 1328.83, 5321.01, 1297.07, 5305.5, 1232.8], [5291.16, 1172.89, 5227.5, 1125.67, 5148.11, 1117.32], [5084.16, 1110.6, 5010.56, 1144.02, 5019.55, 1202.75], [5031.1, 1278.14, 5117.42, 1325.81, 5195.38, 1327.65]]
contour03 = [[5064.52, 857.56], [5108.5, 831.579, 5158.82, 763.1, 5101.08, 714.075], [5020.6, 645.417, 4842.01, 716.914, 4857.13, 813.681], [4869.43, 897.886, 5000.01, 895.218, 5064.52, 857.56]]
contour04 = [[4917.68, 1456.77], [4986.21, 1474.46, 5056.17, 1448.3, 5044.79, 1375.9], [5035.08, 1310.39, 4959.98, 1256.1, 4889.12, 1250.94], [4829.01, 1246.79, 4779.39, 1279.52, 4791.29, 1335.62], [4804.87, 1397.65, 4857.47, 1441.32, 4917.68, 1456.77]]
contour05 = [[4908.21, 966.015], [4877.98, 908.501, 4771.38, 802.499, 4682.57, 770.841], [4624.39, 750.075, 4581.83, 782.293, 4576.26, 835.201], [4574.22, 854.653, 4576.22, 865.482, 4591.15, 913.988], [4620.39, 1008.83, 4607.97, 1034.68, 4571.12, 1107.96], [4551.29, 1147.38, 4545.49, 1162.46, 4541.3, 1185.06], [4531.02, 1238.7, 4571.51, 1275.11, 4613.3, 1279.51], [4627.5, 1281, 4664.7, 1276.1, 4693.07, 1269.07], [4735.43, 1258.68, 4778.97, 1240.45, 4821.67, 1215.38], [4896.71, 1171.47, 4960.91, 1066.09, 4908.21, 966.015]]

# Eine Pfote
contours = []
contours.extend([contour01, contour02, contour03, contour04, contour05])

# Erstellen der Einzelpfote als Zeichen
pfote = font.createChar(0xF273F, "pfote")
pfote.comment = 'Gerne den Vorschlag von Christine Fraunhofer hier umgesetzt!'
pen = pfote.glyphPen();

for i, cnts in enumerate(contours):
    for x, cnt in enumerate(cnts):
        if x == 0:
            pen.moveTo( cnt[0], cnt[1] )
        else:
            pen.curveTo( (cnt[0], cnt[1]), (cnt[2], cnt[3]), (cnt[4], cnt[5]) )
            if x == ( len(cnts) -1 ):
                pen.closePath()
pen = None
pfote.left_side_bearing = pfote.right_side_bearing = 120

# Nun Einzelpfote kopieren, drehen ändern und ein weiteres Zeichen erstellen.
t1 = psMat.compose(psMat.rotate(math.radians(2)), psMat.translate(0, -50))
t2 = psMat.compose(psMat.scale(0.95), psMat.translate(-1500, -500))
t3 = psMat.compose(psMat.scale(0.9), psMat.translate(-3000, -100))
t4 = psMat.compose(psMat.scale(0.85), psMat.translate(-4500, -600))
pfotelig = font.createChar(0xF2740, 'pfote.lig')
pfotelig.addReference("pfote", t1)
pfotelig.addReference("pfote", t2)
pfotelig.addReference("pfote", t3)
pfotelig.addReference("pfote", t4)
pfotelig.unlinkRef()
pfotelig.left_side_bearing = pfotelig.right_side_bearing = 180
pfotelig.comment = 'Hier wurde die Pfote aus "pfote" übernommen, vervielfältigt und transformiert.'

# PAW PRINTS
paws =  font.createChar(0x1F43E, 'u1F43E')
paws.addReference("pfote", psMat.compose(psMat.rotate(math.radians(90)), psMat.translate(-800, 600)))
paws.addReference("pfote", psMat.compose(psMat.rotate(math.radians(90)), psMat.translate(0, -150)))
paws.unlinkRef()
paws.left_side_bearing = paws.right_side_bearing = 90

# Weitere Methode zur Einbettung eines Zeichens:
# SVG inline + tempfile
svg_notdef = '<svg viewBox="0 -410 1437 2048" xmlns="http://www.w3.org/2000/svg"><path d="M120 29h1197v1990H120V29zm771 818c-19.146 0-35.663 6.969-48.204 19C826.57 881.566 817 905.608 817 934c0 19 5 37 14 52 14.526 23.042 31.06 42.069 54 55.322 22.856 13.205 52.073 20.678 92 20.678h243c5-8 48-26 48-35 0-.153-129 5-129 5l-1-1-204-862c39.008 0 115.19-4.337 118-24h-91c-169 0-297-11-447-11-69.382 0-124.94 33.19-163 74.565-26.673 28.993-44.76 62.006-53 90.435-9 37-13 72-13 111 0 120.28 73 209.13 73 317 0 8-1 16-1 23-6 50-41 142-63 142-1 0-3 0-4-1 0-1 4-17 4-32 0-29.87-27.211-45-51-45-32.613 0-55 31.419-55 61v4c3.691 30.763 33.041 55 63 55 43.703 0 87.129-23.289 124-55.122 33.154-28.624 61.009-64.156 79-95.878 7-18 10-31 10-45 0-5 1-10 0-16-3.404-22.981-11.699-44.83-22.648-66-14.214-27.48-32.901-53.817-51.173-80C356.378 527.564 324 479.654 324 426c0-5 3-7 5-7 8.177 0 19.186 48.815 26 65 6.65 16.151 21.424 49.677 42.499 86 16.178 27.883 36.069 57.414 58.849 82 10.016 10.81 20.59 20.663 31.652 29 17.163 14.043 35.68 17.807 54 20.998 16.904 2.945 33.644 5.404 49 15.002v-15c0-35-14-72-34-97-16.056-20.219-31.443-35.644-46-47.926-18.846-15.901-36.297-26.536-52-35.486-33.358-19.014-58.826-30.427-73-68.588-17-49-20-55-26-78-1-2-1-3-1-4 0-2 1-3 3-3 27 34 53 45 76 45 44.057 0 96-45.034 96-79 0-3-1-5-4-6-18 21-41 31-62 31-18.748 0-34.352-7.862-46.034-20C406.581 323.016 398 299.618 398 277c0-23 8-48 26-73 21-28 43-40 76-40-11 27-28 60-28 88 0 40.121 37.28 60 74 60 60.208 0 98-58.732 98-105v-9c0-1-1 0-1 0-6 0-26 33-26 33-9 17-34 35-55 35-29.096 0-40-32.585-40-59 0-17.711 3.44-41 19-41 59.522 0 136.8 4 203 4l-11 42c-4.575 17.156-21.36 34.749-40.38 53-13.85 13.289-28.885 26.928-41.252 41C636.171 323.291 625 341.238 625 360v6c0 29 14 52 50 52h6l-34 174-54-73c-4-4-5-7-5-11 0-11 12-24 12-41 0-29.261-33.666-54-58-54h-3c-15.488 0-32.508 5.268-46 14.77-14.552 10.249-25 25.424-25 44.23 0 13.622 4.023 28.9 11.265 41 7.643 12.772 18.871 22 32.735 22 14.412 0 24.504 1.745 32 4.731 18.509 7.375 21.188 22.321 34 37.27 18 22 56 71 56 71l-32 107c-5.998 17.111-13.023 30.364-20.73 41-16.259 22.437-35.549 33.22-54.623 44-23.132 13.073-45.946 26.145-62.648 60 35-4 56-11 73-11 19.643 0 30 16.54 30 37 0 25-18 46-36 60-42 34-84 44-157 75 1.54-.032 202.74-2 275-2 20.139 0 38.683-4.425 55-12.302 20.715-10 37.84-25.562 50.077-44.699 13.384-20.927 20.923-46.128 20.923-73 0-29.999-11.199-55.33-29.485-71-12.592-10.79-28.544-17-46.515-17h-1c-10 0-20 2-30 5-13-15-23-31-23-52 0-8 1-16 5-26l19-68 68 102c8 9 14 15 21 15s15-7 26-26l104-195 51 265c-15-9-32-14-48-14zm-6-676 195 856h-60L849 171h36zm-117 0h34l37.977 184 10.32 50 15.48 75 7.224 35-13.274 25-20.177 38L813 628l-97-141 11-61c12 2 22 4 31 4 35 0 46-21 46-50v-3c0-26.951-16.105-62.152-28.13-96-7.159-20.155-12.87-39.831-12.87-57v-8zm-64 382 84 121-33 60-69-95zm-92 402c0-28.731 11.707-48 40-48 14 0 30 7 48 22-5-19-7-47-18-60 5-1 9-1 13-1h2c15.94 0 27.386 5.288 34.744 16C738.696 894.12 742 909.082 742 929c0 14-4 19-9 30-7.97-11.07-18.883-17.827-31-21.92-15.246-5.148-32.399-6.08-48-6.08-7 0-13-1-19 0 43 18 60 32 60 66 0 15-23 27-40 27-31.975 0-43-40.368-43-69zm293-86c12 0 24 4 37 11l8 51c-12 0-23-2-34-2-22 0-42 7-59 30-5-10-8-15-8-28v-2c0-17.639 7.446-34.63 19.76-46 9.327-8.612 21.448-14 35.24-14h1zm34 77c4 0 8 0 13 1l11 80h-4c-18.746 0-40.073-4.195-55-11.852-11.351-5.822-19-13.646-19-23.148v-5c0-11.568 4.425-22.308 14-29.891 8.634-6.838 21.456-11.109 39-11.109h1z" fill="currentColor"/></svg>'

temp = tempfile.NamedTemporaryFile(suffix=".svg", mode="w+t")
temp.writelines( svg_notdef )
temp.seek(0)
gl_notdef = font.createChar(0x25A1, '.notdef')
gl_notdef.importOutlines( temp.name )
gl_notdef.left_side_bearing = gl_notdef.right_side_bearing = 90

# some hands / import der svg-Datei
# dann die jeweiligen Symbole
svg_hand = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 0 1691 2048"><path fill="currentColor" d="M650.924 633.347zm940.846 308.775c-66.88-27.222-170.992-46.161-213.351-36.45-8.33 1.91-16.262 5.635-24.067 9.347 10.805 14.014 17.598 29.86 26.532 68.826 8.932 38.964-11.224 104.117-35.092 132.705-.464.558-.624 1.112-.497 1.664 3.6 15.709 239.516 28.674 242.902 43.45.045.196-.197.36-.745.485-102.893 23.588-210.852-6.784-289.348-20.066-95.085-17.536-688.318 64.168-716.393-57.154-6.185-26.782 10.032-28.006 15.002-35.158-36.71-6.183-54.237-24.256-70.792-43.397-2.25-2.599-3.722-5.377-4.406-8.36-1.859-8.109 2.117-17.725 12.203-29.323 0 0-54.696-26.18-62.415-59.855-2.088-9.104 7.328-20.474 5.505-28.42-3.502-15.281-369.793 60.107-386.551-12.99-4.426-19.306 48-40.255 125.157-57.944 199.646-45.767 370.17-52.681 540.533-40.907-52.313-45.58-130.495-112.98-139.03-150.208-3.336-14.55-.004-23.383 8.708-25.38a16.387 16.387 0 0 1 1.724-.3c142.961-17.132 434.483 329.88 720.735 289.698 178.02-24.988 243.684 59.737 243.684 59.737zm-850.178 4.307c-27.75 6.363-104.319 16.94-156.101 28.813-16.923 3.88-27.414 9.318-25.621 17.138 3.56 15.525 27.179 35.443 64.491 31.21 34.808-3.952 102.057-10.007 123.274-10.847 27.608-2.82 42.974-1.515 43.818 2.16.8 3.489-11.485 9.115-38.803 15.378-25.837 5.923-60.36 11.562-95.824 19.691-2.909.668-5.905 1.28-8.938 1.974-10.696 2.454-30.136 10.01-25.148 31.77 1.286 5.602 8.032 11.978 23.862 19.115 73.128 33.622 500.958 16.864 558.664 3.635 44.203-10.134 91.89-82.526 78.978-138.839-14.67-64.004-114.272-75.994-183.108-95.546-66.383-18.853-198.512-118.758-312.846-186.255-30.36-17.925-119.325-71.884-138.117-67.575-2.862.656-4.095 2.662-3.25 6.352.518 2.258 1.817 5.15 4.001 8.75 25.428 41.91 116.89 114.868 170.301 148.356 8.527 5.344 13.216 9.68 13.845 12.42.485 2.115-1.039 3.867-3.44 4.417-.486.11-1.011.156-1.562.18-69.963 3.007-147.299-8.981-224.798-8.884-116.126.148-273.439 15.156-376.448 38.769-39.594 9.079-114.52 26.382-112.559 34.95.924 4.027 4.684 8.31 12.278 12.445 37.73 20.49 499.19-28.85 528.754-32.31 49.357-5.314 73.844-4.445 75.126 1.151.506 2.21-4.234 5.393-13.894 9.074-47.784 8.34-143.493 15.28-189.728 25.878-18.683 4.285-22.605 15.988-17.345 38.933 2.094 9.127 43.515 31.115 54.725 28.927 3.818-.746 195.052-30.057 199.356-11.274.619 2.707-7.556 6.287-23.944 10.043z"/></svg>'
svg_hand_black = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 0 1620 2048"><path fill="currentColor" d="M530.898 563.521c0-6.518 6.346-11.546 16.167-11.546 18.375 0 57.072 15.321 96.677 31.446 218.56 88.984 324.17 214.276 508.786 333.585 61.222 39.565 143.07 37.869 214.41 43.015 21.005 27.964 30.617 65.43 30.617 103.307 0 74.513-32.39 152.032-91.814 157.672-5.126.486-11.341.774-18.5.774-15.272 0-34.843-1.312-57.327-4.813-250.173-38.961-473.173-14.962-631.173-34.862-31.515-3.97-40.563-20.751-40.563-34.018 0-37.726 61.225-43.041 113.01-43.041 20.318 0 39.183.818 52.326.818 2.61 0 4.995-.032 7.121-.109-10.82-17.056-33.312-17.826-50.136-17.826-1.67 0-3.285.008-4.826.008-21.377 0-45.191 2.249-67.417 2.249-9.9 0-20.313.228-30.67.228-43.209 0-85.443-3.977-85.443-45.12 0-45.575 57.812-40.864 100.519-46.832 31.951-4.465 73.08-3.456 101.34-6.703-9.11-12.48-35.4-15.914-66.38-15.914-37.913 0-82.85 5.143-111.912 5.143-39.297 0-90.14-9.23-90.14-51.329 0-10.508 10.97-22.65 33.417-24.887C582.697 892.437 656.743 884 656.743 884c-17.405-13.327-65.04-17.729-127.333-17.729-121.244 0-298.021 16.675-415.518 16.675-39.567 0-72.412-1.89-94.15-6.946C5.855 872.77 0 866.433 0 860.19c0-6.282 6.365-12.83 16.742-19.72 78.009-51.791 429.316-69.622 662.934-69.622 6.687 0 26.847 1.213 44.446 1.213 15.843 0 29.612-.983 29.612-4.72 0-5.195-11.67-13.519-19.245-19.25C692 715.95 588.698 647.737 545.2 603c-8.878-16.127-14.302-29.86-14.302-39.479zM1393.33 959.89c23.05-7.786 48.768-11.202 75.033-11.202 31.06 0 62.884 4.777 91.965 12.755 28.52 10.707 39.33 56.857 39.33 106.313 0 63.977-18.804 131.23-39.33 138.959-56.264 21.184-143.798 16.777-202.765 19.821 40.374-21.952 68.751-89.355 68.751-159.809 0-36.794-9.991-74.42-32.984-106.838z"/></svg>'
temp = tempfile.NamedTemporaryFile(suffix=".svg", mode="w+t")
tempb = tempfile.NamedTemporaryFile(suffix=".svg", mode="w+t")
temp.writelines( svg_hand )
tempb.writelines( svg_hand_black )
temp.seek(0)
tempb.seek(0)
gl_hand_white = font.createChar(0x1FFFE, 'u1FFFE')
gl_hand_white.importOutlines( temp.name )
gl_hand_white.width = (font.em * int(0.8))
gl_hand_white = gl_hand_white.round(1)
gl_hand_white.left_side_bearing = gl_hand_white.right_side_bearing = 0

# BLACK LEFT POINTING INDEX
gl_b_left = font.createChar(0x261A, 'u261A')
gl_b_left.importOutlines( tempb.name )
gl_b_left.width = (font.em * int(0.8))
gl_b_left = gl_b_left.round(1)
gl_b_left.left_side_bearing = gl_b_left.right_side_bearing = 48

# BLACK RIGHT POINTING INDEX
gl_b_right = font.createChar(0x261B, 'u261B')
gl_b_right.importOutlines( tempb.name )
gl_b_right.width = (font.em * int(0.8))
gl_b_right = gl_b_right.round(1)
gl_b_right.layers[1] = gl_b_right.layers[1].transform(psMat.scale(-1,1))
gl_b_right.left_side_bearing = gl_b_right.right_side_bearing = 48

# SIDEWAYS WHITE LEFT POINTING INDEX
gl_side_w_left = font.createChar(0x1F598, 'u1F598')
gl_side_w_left.layers[1] = gl_hand_white.layers[1]
gl_side_w_left.left_side_bearing = gl_side_w_left.right_side_bearing = 48

# SIDEWAYS WHITE RIGHT POINTING INDEX
gl_side_w_right = font.createChar(0x1F599, 'u1F599')
gl_side_w_right.layers[1] = gl_hand_white.layers[1].transform(psMat.scale(-1,1))
gl_side_w_right.left_side_bearing = gl_side_w_right.right_side_bearing = 48

# SIDEWAYS WHITE UP POINTING INDEX
gl_side_w_up = font.createChar(0x1F59E, 'u1F59E')
gl_side_w_up.layers[1] = gl_hand_white.layers[1].transform(psMat.rotate(math.radians(-90)))

# SIDEWAYS WHITE DOWN POINTING INDEX
gl_side_w_down = font.createChar(0x1F59F, 'u1F59F')
gl_side_w_down.layers[1] = gl_hand_white.layers[1].transform(psMat.rotate(math.radians(90)))

# WHITE LEFT POINTING BACKHAND INDEX
gl_w_left = font.createChar(0x1F448, 'u1F448')
gl_w_left.layers[1] = gl_side_w_left.layers[1]
gl_w_left.left_side_bearing = gl_w_left.right_side_bearing = 48

# WHITE RIGHT POINTING BACKHAND INDEX
gl_w_right = font.createChar(0x1F449, 'u1F449')
gl_w_right.layers[1] = gl_side_w_right.layers[1]
gl_w_right.left_side_bearing = gl_w_right.right_side_bearing = 48

# WHITE UP POINTING BACKHAND INDEX
gl_w_up = font.createChar(0x1F446, 'u1F446')
gl_w_up.layers[1] = gl_hand_white.layers[1].transform(psMat.rotate(math.radians(-90)))

# WHITE DOWN POINTING BACKHAND INDEX
gl_w_down = font.createChar(0x1F447, 'u1F447')
gl_w_down.layers[1] = gl_hand_white.layers[1].transform(psMat.rotate(math.radians(90)))

# Stylistic Sets, normale und besondere Ligaturen.
# ss01
char = font.createChar(0x61)
char.addPosSub('ss01', 'a.ss01')
char = font.createChar(0x64)
char.addPosSub('ss01', 'd.ss01')
char = font.createChar(0x65)
char.addPosSub('ss01', 'e.ss01')
char = font.createChar(0x69)
char.addPosSub('ss01', 'i.ss01')
char = font.createChar(0x6D)
char.addPosSub('ss01', 'm.ss01')
char = font.createChar(0x6E)
char.addPosSub('ss01', 'n.ss01')
char = font.createChar(0x6F)
char.addPosSub('ss01', 'o.ss01')
char = font.createChar(0x72)
char.addPosSub('ss01', 'r.ss01')
char = font.createChar(0x73)
char.addPosSub('ss01', 's.ss01')
char = font.createChar(0x74)
char.addPosSub('ss01', 't.ss01')

# ss02
char = font.createChar(0x61)
char.addPosSub('ss02', 'a.ss02')
char = font.createChar(0x65)
char.addPosSub('ss02', 'e.ss02')

# liga
char = font.createChar(64256)
char.addPosSub('liga', tuple(['f', 'f']))
char = font.createChar(64257)
char.addPosSub('liga', tuple(['f', 'i']))
char = font.createChar(64258)
char.addPosSub('liga', tuple(['f', 'l']))
char = font.createChar(64259)
char.addPosSub('liga', tuple(['f', 'f', 'i']))
pfotelig.addPosSub('liga', tuple(['S', 'a', 'm', 't', 'p', 'f', 'o', 't', 'e']))

# dlig
char = font.createChar(0xF273A)
char.addPosSub('dlig', tuple(['c', 'k']))
char = font.createChar(0xF273B)
char.addPosSub('dlig', tuple(['Q', 'u']))
char = font.createChar(0xF273C)
char.addPosSub('dlig', tuple(['s', 's']))
char = font.createChar(0xF273D)
char.addPosSub('dlig', tuple(['e', 'i']))
char = font.createChar(0xF273E)
char.addPosSub('dlig', tuple(['t', 't']))

# INVERTED EXCLAMATION MARK
exclamdown = font.createChar(0xA1, 'exclamdown')
exclamdown.addReference('exclam', psMat.rotate(math.radians(180)))
exclamdown.unlinkRef()
exclamdown.comment = 'Umgedrehtes Ausrufezeichen.'

# SOFT HYPHEN
softhyphen = font.createChar(0xAD, 'uni00AD')
softhyphen.addReference('hyphen')
softhyphen.left_side_bearing = softhyphen.right_side_bearing = 48
softhyphen.comment = 'SHY, referenziert.'

# SUPERSCRIPT ONE
supone = font.createChar(0xB9, 'uni00B9')
supone.addReference('one', psMat.compose(psMat.scale(0.5), psMat.translate(0, 1000)))
supone.unlinkRef()
supone.left_side_bearing = supone.right_side_bearing = 48
supone.comment = 'superscript one, nicht referenziert.'

# SUPERSCRIPT TWO
suptwo = font.createChar(0xB2, 'uni00B2')
suptwo.addReference('two', psMat.compose(psMat.scale(0.5), psMat.translate(0, 1000)))
suptwo.unlinkRef()
suptwo.left_side_bearing = suptwo.right_side_bearing = 48
supone.comment = 'superscript two, nicht referenziert.'

# SUPERSCRIPT THREE
supthree = font.createChar(0xB3, 'uni00B3')
supthree.addReference('three', psMat.compose(psMat.scale(0.5), psMat.translate(0, 1000)))
supthree.unlinkRef()
supthree.left_side_bearing = supthree.right_side_bearing = 48
supthree.comment = 'superscript three, nicht referenziert.'

# INVERTED QUESTION MARK
questiondown = font.createChar(0xBF, 'questiondown')
questiondown.addReference('question', psMat.rotate(math.radians(180)))
questiondown.unlinkRef()
questiondown.comment = 'Umgedrehtes Fragezeichen.'

# INVERTED INTERROBANG
interrobangdown = font.createChar(0x2E18, 'uni2E18')
interrobangdown.addReference('uni203D', psMat.rotate(math.radians(180)))
interrobangdown.unlinkRef()
interrobangdown.comment = 'Umgedrehtes Fragezeichen.'

# Hier der Versuch bestimmte durchschnittliche Annahmen über die Zeichengrößen
# automagisch umzusetzen.
# get Font-Spezifika
fEm           = font.em
fDesc         = font.descent
fAsc          = font.ascent

# set Font-Spezifika
xHeight = round((fAsc/1.9),1)

xHeightLine = fontforge.contour()
xHeightLine.moveTo(-font.em, xHeight * 0.9)
xHeightLine.lineTo(1.8 * font.em, xHeight * 0.9)
font.guide += xHeightLine

baseToX       = xHeight
baseToMax     = round((fAsc/1.03),1)
baseToMaxLess = round((fAsc/1.09),1)

maxLessLine = fontforge.contour()
maxLessLine.moveTo(-font.em, baseToMaxLess)
maxLessLine.lineTo(1.8 * font.em, baseToMaxLess)
font.guide += maxLessLine

baseMin       = round((fDesc/1.08),1)
minToX        = baseMin + xHeight
minToMax      = baseMin + baseToMax
minToMaxLess  = baseMin + baseToMaxLess

baseToMaxGlyphs = ["exclam", "numbersign", "dollar", "percent", "ampersand", "parenleft", "parenright", "slash", "question",  "A", "B", "C", "D", "E", "F", "H", "I", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "bracketleft", "backslash", "bracketright", "braceleft", "bar", "braceright", "section", "Adieresis", "Odieresis", "Udieresis", "Euro", "Q_u.liga"]
baseToXGlyphs = ["at", "a", "c", "e", "i", "m", "n", "o", "r", "s", "u", "v", "w", "x", "z", "adieresis", "odieresis", "udieresis", "a.ss01", "a.ss02", "e.ss01", "e.ss02", "i.ss01", "m.ss01", "n.ss01", "o.ss01", "r.ss01", "s.ss01", "s_s.liga", "e_i.liga"]
baseToMaxLessGlyphs = ["b", "d", "h", "k", "l", "t", "onequarter", "onehalf", "threequarters", "d.ss01", "t.ss01", "c_k.liga", "t_t.liga", "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "u1F59E", "u1F59F", "u1F446", "u1F447"]
minToXGlyphs = ["g", "j", "p", "q", "y", "exclamdown", "questiondown", "uni2E18"]
minToMaxLessGlyphs = ["f", "germandbls", "uniFB00", "uniFB01", "uniFB02", "uniFB03"]

adjustGlyphs = []
adjustGlyphs.extend([
    baseToMaxGlyphs,
    baseToXGlyphs,
    baseToMaxLessGlyphs,
    minToXGlyphs,
    minToMaxLessGlyphs
])

for i, glyphs in enumerate( adjustGlyphs ):
    for j, glyph in enumerate( glyphs ):
        # jeweiliges Zeichen
        gl = font[ glyph ]
        # Koordinaten des Zeichens
        (xMin, yMin, xMax, yMax) = gl.boundingBox()
        xMin = round( xMin, 1 )
        yMin = round( yMin, 1 )
        xMax = round( xMax, 1 )
        yMax = round( yMax, 1 )
        # Versatz von jeweiliger Grundlinie
        if i == 0:
            glToBase = -yMin -15
            glToHeight = round((baseToMax / (yMax - yMin)),1)
            baseAndScale = psMat.compose(psMat.translate( 0, glToBase ), psMat.scale( glToHeight ))
        elif i == 1:
            glToBase = -yMin -15
            glToHeight = round((baseToX / (yMax - yMin)),1)
            baseAndScale = psMat.compose(psMat.translate( 0, glToBase ), psMat.scale( glToHeight ))
        elif i == 2:
            glToBase = -yMin -15
            glToHeight = round((baseToMaxLess / (yMax - yMin)),1)
            baseAndScale = psMat.compose(psMat.translate( 0, glToBase ), psMat.scale( glToHeight ))
        elif i == 3:
            glToHeight = round((minToX / (yMax - yMin)),1)
            negCorr = psMat.translate( 0, -yMin );
            baseAndScale = psMat.compose(negCorr, psMat.compose(psMat.scale( glToHeight ), psMat.translate( 0, -baseMin )))
        elif i == 4:
            glToHeight = round((minToMaxLess / (yMax - yMin)),1)
            negCorr = psMat.translate( 0, -yMin );
            baseAndScale = psMat.compose(negCorr, psMat.compose(psMat.scale( glToHeight ), psMat.translate( 0, -baseMin )))
        gl.transform( baseAndScale )
        gl.left_side_bearing = gl.right_side_bearing = 48

gl_hand_white.clear()

# tidy
font.selection.all()
font.correctDirection()
font.removeOverlap()
font.simplify()
font.round()
font.addExtrema()

# Ausgabe
font.save(pfad + name + "-Regular.sfd")
# font.generate(pfad + name + "-Regular.otf")

font.close()
