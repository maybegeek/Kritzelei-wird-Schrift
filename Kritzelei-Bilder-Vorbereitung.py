#!/usr/bin/env python3
# coding: utf-8
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### 
# de-warp scans
# Vorbereitung zur Fontifizierung
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### 
# Author:  Christoph Pfeiffer
# Date:    Juni 2021
# License: CC (BY-NC-SA 4.0) 
# https://creativecommons.org/licenses/by-nc-sa/4.0/
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### 

import cv2
import numpy as np
import cv2.aruco as aruco
import matplotlib.pyplot as plt

## Originalbild, schiefer Scan oder Handyfoto
BILD_ORIGINAL = cv2.imread("Kritzelei-Bilder-Original/A.jpg")
# imgtest = plt.imshow(BILD_ORIGINAL)
# plt.show()

## Arbeitskopie
BILD_WORK = BILD_ORIGINAL.copy()

## cv2-Import-Farbennotation zu grau
BILD_WORK = cv2.cvtColor(BILD_WORK, cv2.COLOR_BGR2GRAY)

## default-werte passen
parameters = aruco.DetectorParameters_create()
## welche arucos sollen erkannt werden
aruco_dict = aruco.Dictionary_get(aruco.DICT_6X6_50)

## hier also nun die Markersuche
corners, ids, rejectedImgPoints = aruco.detectMarkers(BILD_WORK, aruco_dict, parameters=parameters)

## Marker mit ID0 = links-oben = 0
## Marker mit ID1 = rechts-oben = 1
## Marker mit ID2 = rechts-unten = 2
## Marker mit ID3 = links-unten = 3

## Die aruco-Marker nach ID/Reihenfolge
marker_0 = np.where(ids == 0)
marker_1 = np.where(ids == 1)
marker_2 = np.where(ids == 2)
marker_3 = np.where(ids == 3)

## vier-Punkte der vier Marker
corner_0 = corners[ marker_0[0][0] ]
corner_1 = corners[ marker_1[0][0] ]
corner_2 = corners[ marker_2[0][0] ]
corner_3 = corners[ marker_3[0][0] ]

## nun die jeweiligen Koordinatenpaare
## der innenliegenden Punkte der jeweiligen Marker
corner_0_cut = corner_0[0][2]
corner_1_cut = corner_1[0][3]
corner_2_cut = corner_2[0][0]
corner_3_cut = corner_3[0][1]

## Position der innenliegenden Koordinatenpaare zur Weiterverarbeitung
cut_punkte_orig = np.float32( [ corner_0_cut, corner_1_cut, corner_2_cut, corner_3_cut ] )

## das hilft eigtl. nix und führt nur zu verzerrungen
## verhältnis des inneren sollte
## 1x (Breite) zu 1,26x Höhe sein
## `opinionated` Zielbreite aus Mittel von oben-und-unten-Breite
# zielbreite = int(round( ( corner_1_cut[0] - corner_0_cut[0] +  corner_2_cut[0] - corner_3_cut[0] ) / 2 ))


## oder evtl. diesen wert und daraus dann die Breite mit 0,79x die Höhe
## `opinionated` Zielhoehe aus Mittel von links-und-rechts-Hoehe
zielhoehe = int(round( ( corner_3_cut[1] - corner_0_cut[1] +  corner_2_cut[1] - corner_1_cut[1] ) / 2 ))

zielbreite = int(round( zielhoehe * 0.795 ))
#in version 3 breite ist 0.7063 mal die höhe
## Zielbild-Dimensionen
fix_punkte_ziel = np.float32( [ [0,0], [zielbreite,0], [zielbreite,zielhoehe], [0,zielhoehe] ]   )

## Transformationsmatrix
M = cv2.getPerspectiveTransform( cut_punkte_orig, fix_punkte_ziel )

## Hier nun die Umwandlung
BILD_DEWARP = cv2.warpPerspective( BILD_WORK, M, (zielbreite, zielhoehe) )

## entzerrtes Bild speichern
cv2.imwrite( "Kritzelei-Bilder-Vorbereitung/A.jpg", BILD_DEWARP)

## Hier Darstellung als Diagramm
## Originalbild BGR2RGB
BILD_ORIGINAL = cv2.cvtColor(BILD_ORIGINAL, cv2.COLOR_BGR2RGB)
plt.subplot(121),plt.imshow(BILD_ORIGINAL),plt.title("Original")
plt.subplot(122),plt.imshow(BILD_DEWARP, cmap='gray'),plt.title("zur Weiterverarbeitung")
plt.show()

#waits for user to press any key
#(this is necessary to avoid Python kernel form crashing)
cv2.waitKey(0)

#closing all open windows
cv2.destroyAllWindows()
