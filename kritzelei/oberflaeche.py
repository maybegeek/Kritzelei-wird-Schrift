"""Bedienoberfläche (CustomTkinter): führt in sechs Schritten von den Fotos zur Schrift.

Die Arbeit erledigen die Kommandozeilen-Skripte, siehe ``auftrag.py``. Das
aufklappbare Protokoll zeigt jeden Aufruf und alle Ausgaben.
"""

from __future__ import annotations

import os
import queue
import shlex
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, font as tkfont

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps, ImageTk

from . import auftrag, schriftprobe
from .auftrag import pfad

BILDER = auftrag.WURZEL / "template" / "oberflaeche"
AUTOR = "Christoph Pfeiffer"
LINKS = (("Projektseite", "https://maybegeek.github.io/Kritzelei-wird-Schrift/"),
         ("Quellcode auf GitHub", "https://github.com/maybegeek/Kritzelei-wird-Schrift"),
         ("Weiterentwicklung von Hand2Font", "https://maybegeek.github.io/Hand2Font/"))
LIZENZ = ("CC BY-NC-SA 4.0", "https://creativecommons.org/licenses/by-nc-sa/4.0/")
ZEICHENVORLAGE = auftrag.WURZEL / "Kritzelei-Zeichenvorlage" / "Kritzelei-Zeichenvorlage.pdf"

SCHRIFTPROBE_TEXT = (
    "Franz jagt im komplett verwahrlosten Taxi quer durch Bayern.\n"
    "Zwölf Boxkämpfer jagen Viktor quer über den großen Sylter Deich.\n"
    "0123456789 – Kritzelei wird Schrift!"
)
FONTFORGE_WARTEZEIT = 3000  # ms bis zur Kontrolle, ob FontForge noch läuft
PLATZ = 44  # Seitenrand des Inhalts

# CustomTkinter zeichnet Rundungen unter Linux als Schriftzeichen. Sie treffen die geraden Kanten
# nur bei manchen Radien sauber: 7, 10, 12, 20, 22, 25, 27 passen, 16, 18, 21, 23 wirken gewölbt.
RADIUS_KARTE = 20
RADIUS_FELD = 12
RADIUS_KNOPF = 22  # bei Höhe 44 eine Pille
RADIUS_RAND_KNOPF = 20  # mit Rand: Der innere Radius (eins kleiner) soll auch noch passen

AKZENT = "#4346E0"
AKZENT_HELL = "#5B5EF0"
AKZENT_DUNKEL = "#3336BE"
TON = "#ECECFD"
PAPIER = "#FBFAF7"
KARTE = "#FFFFFF"
FELD = "#F2F1EC"
TINTE = "#1E2138"
GRAU = "#6B6E80"
LINIE = "#E7E5DE"
FARBEN = {"hinweis": GRAU, "ok": "#1B7A3D", "warnung": "#A85A00", "fehler": "#B3261E"}

# Große Buchstaben bringen bis zu 2 Pixel eigenen Vorlauf mit (das „E“ mehr als das „A“). Damit kein
# kleinerer Text links seiner Überschrift beginnt, sind diese leicht eingerückt. Bei CTkLabel geht das
# über corner_radius: Er wirkt als Innenabstand, und ohne Hintergrund ist keine Rundung zu sehen.
EINZUG_H2 = 2
EINZUG_TEXT = 3

# Dieselben Farben wie raster.markieren, in derselben Bedeutung
LEGENDE = (("#0078FF", "Soll-Raster der Vorlage"), ("#28AA28", "gefundener Rahmen"),
           ("#FF8C00", "Lage geschätzt"), ("#DC0000", "Ausschnitt, der zur Glyphe wird"))

SEITEN = ("Start", "Entzerren", "Erkennung prüfen", "Schrift erzeugen", "Ergebnis", "Schriftschnitte", "Export")
EXPORT_FORMATE = (("otf", "OTF", "zum Installieren", True), ("ttf", "TTF", "zum Installieren, für ältere Programme", False),
                  ("woff2", "WOFF2", "für Webseiten", True), ("ufo", "UFO", "für Glyphs, RoboFont, FontLab, Fontra", True))
SCHNITTE = (("Italic", "Italic"), ("Bold", "Bold"), ("BoldItalic", "Bold-Italic"))


def _familie(wurzel, *wuensche: str) -> str:
    """Die erste installierte Schrift aus der Wunschliste; die Oberfläche soll überall laufen."""
    vorhanden = set(tkfont.families(wurzel))
    return next((w for w in wuensche if w in vorhanden), "TkDefaultFont")


class Stil:
    """Wiederkehrende Bausteine in einheitlicher Gestalt."""

    def __init__(self, wurzel):
        self.sans = _familie(wurzel, "Lato", "Noto Sans", "Cantarell", "DejaVu Sans", "Helvetica", "Arial")
        self.serif = _familie(wurzel, "Noto Serif", "DejaVu Serif", "Georgia", "Times New Roman")
        self.mono = _familie(wurzel, "Noto Sans Mono", "DejaVu Sans Mono", "Menlo", "Consolas")

    def h1(self, eltern, text):
        return ctk.CTkLabel(eltern, text=text, font=(self.sans, 30, "bold"), text_color=TINTE, anchor="w")

    def h2(self, eltern, text):
        return ctk.CTkLabel(eltern, text=text, font=(self.sans, 16, "bold"), text_color=TINTE, anchor="w",
                            corner_radius=EINZUG_H2)

    def fett(self, eltern, text):
        return ctk.CTkLabel(eltern, text=text, font=(self.sans, 13, "bold"), text_color=TINTE, anchor="w", height=20,
                            corner_radius=EINZUG_TEXT)

    def text(self, eltern, text="", breite=720, groesse=14, farbe=TINTE):
        return ctk.CTkLabel(eltern, text=text, font=(self.serif, groesse), text_color=farbe, anchor="w",
                            justify="left", wraplength=breite, corner_radius=EINZUG_TEXT)

    def klein(self, eltern, text="", farbe=GRAU, breite=0):
        return ctk.CTkLabel(eltern, text=text, font=(self.sans, 13), text_color=farbe, anchor="w",
                            justify="left", wraplength=breite, corner_radius=EINZUG_TEXT)

    def haupt(self, eltern, text, befehl=None):
        return ctk.CTkButton(eltern, text=text, command=befehl, height=44, corner_radius=RADIUS_KNOPF, border_spacing=18,
                             font=(self.sans, 15, "bold"), fg_color=AKZENT, hover_color=AKZENT_DUNKEL,
                             text_color="white", text_color_disabled="#C9CAF5")

    def neben(self, eltern, text, befehl=None, hoehe=44, breite=96):
        return ctk.CTkButton(eltern, text=text, command=befehl, height=hoehe, width=breite,
                             corner_radius=RADIUS_RAND_KNOPF if hoehe >= 40 else RADIUS_FELD, border_spacing=6,
                             font=(self.sans, 14),
                             fg_color="transparent", hover_color=TON, text_color=AKZENT,
                             text_color_disabled="#A9AAC0", border_width=1, border_color=AKZENT)

    def als_haupt(self, knopf: ctk.CTkButton) -> None:
        knopf.configure(fg_color=AKZENT, hover_color=AKZENT_DUNKEL, text_color="white", border_width=0,
                        corner_radius=RADIUS_KNOPF, font=(self.sans, 15, "bold"))

    def als_neben(self, knopf: ctk.CTkButton) -> None:
        knopf.configure(fg_color="transparent", hover_color=TON, text_color=AKZENT, border_width=1,
                        border_color=AKZENT, corner_radius=RADIUS_RAND_KNOPF, font=(self.sans, 14))

    def karte(self, eltern, **optionen):
        return ctk.CTkFrame(eltern, fg_color=KARTE, corner_radius=RADIUS_KARTE, border_width=1, border_color=LINIE, **optionen)

    def feld(self, eltern, variable, breite=140):
        return ctk.CTkEntry(eltern, textvariable=variable, height=44, width=breite, corner_radius=RADIUS_FELD, border_width=0,
                            fg_color=FELD, text_color=TINTE, font=(self.sans, 14))

    def haken(self, eltern, text, variable):
        return ctk.CTkCheckBox(eltern, text=text, variable=variable, width=24, font=(self.sans, 14), text_color=TINTE,
                               fg_color=AKZENT, hover_color=AKZENT_DUNKEL, border_color="#B8B8C8",
                               checkbox_width=20, checkbox_height=20, corner_radius=6, border_width=2)


def _kreis(farbe: str, durchmesser: int = 30) -> ctk.CTkImage:
    bild = Image.new("RGBA", (durchmesser * 4, durchmesser * 4), (0, 0, 0, 0))
    ImageDraw.Draw(bild).ellipse((0, 0, durchmesser * 4 - 1, durchmesser * 4 - 1), fill=farbe)
    return ctk.CTkImage(bild, size=(durchmesser, durchmesser))


class Dialog(ctk.CTkToplevel):
    """Rückfrage oder Meldung in der Gestalt der Oberfläche; ``warten`` liefert die Antwort."""

    def __init__(self, fenster, stil: Stil, titel: str, text: str, ja: str, nein: str | None = None):
        super().__init__(fenster, fg_color=PAPIER)
        self.withdraw()
        self.title(titel)
        self.resizable(False, False)
        self.antwort = False
        stil.h2(self, titel).pack(anchor="w", padx=28, pady=(24, 6))
        stil.text(self, text, breite=420).pack(anchor="w", padx=28)
        leiste = ctk.CTkFrame(self, fg_color="transparent")
        leiste.pack(fill="x", padx=28, pady=(20, 22))
        self.ja_knopf = stil.haupt(leiste, ja, lambda: self._antworten(True))
        self.ja_knopf.pack(side="right")
        if nein:
            stil.neben(leiste, nein, lambda: self._antworten(False), hoehe=44, breite=110).pack(side="right", padx=10)
        else:
            self.bind("<Return>", lambda _: self._antworten(True))
        self.bind("<Escape>", lambda _: self._antworten(False))
        self.protocol("WM_DELETE_WINDOW", lambda: self._antworten(False))

        self.update_idletasks()
        breite, hoehe = max(self.winfo_reqwidth(), 420), self.winfo_reqheight()
        if fenster.winfo_viewable():
            self.transient(fenster)
            x = fenster.winfo_rootx() + (fenster.winfo_width() - breite) // 2
            y = fenster.winfo_rooty() + (fenster.winfo_height() - hoehe) // 3
            self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()
        self.wait_visibility()
        self.grab_set()
        self.focus_set()

    def _antworten(self, antwort: bool) -> None:
        self.antwort = antwort
        self.grab_release()
        self.destroy()

    def warten(self) -> bool:
        if self.winfo_exists():
            self.wait_window()
        return self.antwort


class Rollflaeche(ctk.CTkFrame):
    """Senkrecht rollbarer Bereich, die Leiste erscheint nur, wenn der Inhalt nicht passt.

    CTkScrollableFrame zeigt seine Leiste immer und schaltet sie auch selbst wieder ein.
    """

    def __init__(self, eltern):
        super().__init__(eltern, fg_color="transparent")
        self._flaeche = tk.Canvas(self, background=PAPIER, highlightthickness=0)
        self._leiste = ctk.CTkScrollbar(self, command=self._flaeche.yview, button_color=LINIE,
                                        button_hover_color="#CFCDC4")
        self._flaeche.configure(yscrollcommand=self._leiste.set)
        self._flaeche.pack(side="left", fill="both", expand=True)
        self.inhalt = ctk.CTkFrame(self._flaeche, fg_color="transparent")
        self._fenster = self._flaeche.create_window(0, 0, window=self.inhalt, anchor="nw")
        self.leiste_sichtbar = False
        tk.Misc.bind(self.inhalt, "<Configure>", self._anpassen, add="+")
        self._flaeche.bind("<Configure>", self._anpassen, add="+")
        for ereignis in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
            self._flaeche.bind_all(ereignis, self._rad, add="+")

    def _anpassen(self, _ereignis=None) -> None:
        breite, hoehe = self._flaeche.winfo_width(), self._flaeche.winfo_height()
        self._flaeche.itemconfigure(self._fenster, width=breite)
        bedarf = self.inhalt.winfo_reqheight()
        self._flaeche.configure(scrollregion=(0, 0, breite, max(bedarf, hoehe)))
        noetig = bedarf > hoehe
        if noetig != self.leiste_sichtbar:
            self.leiste_sichtbar = noetig
            if noetig:
                self._leiste.pack(side="right", fill="y", padx=(6, 0), before=self._flaeche)
            else:
                self._leiste.pack_forget()
        if not noetig:
            self._flaeche.yview_moveto(0)

    def _rad(self, ereignis) -> None:
        # bind_all: Das Ereignis kommt von jedem Widget, gemeint ist nur der eigene Bereich.
        if not self.leiste_sichtbar or not str(ereignis.widget).startswith(str(self)):
            return
        hoch = ereignis.num == 4 or getattr(ereignis, "delta", 0) > 0
        self._flaeche.yview_scroll(-1 if hoch else 1, "units")


class Bildansicht(ctk.CTkFrame):
    """Bilderauswahl mit Anzeige: eingepasst oder in voller Größe (Doppelklick)."""

    def __init__(self, eltern, stil: Stil, leertext: str):
        super().__init__(eltern, fg_color="transparent")
        self.stil = stil
        self.leertext = leertext
        self.dateien: list[Path] = []
        self.auswahl = ""
        self.einpassen = True
        self._bild: Image.Image | None = None
        self._foto = None
        self._nachlauf = None
        self._versatz = (0, 0, 1.0)
        self._knoepfe: dict[str, ctk.CTkButton] = {}

        kopf = ctk.CTkFrame(self, fg_color="transparent")
        kopf.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self._wahl = ctk.CTkFrame(kopf, fg_color="transparent")
        self._wahl.pack(side="left")
        self._zoom = stil.neben(kopf, "Volle Größe", self.umschalten, hoehe=40, breite=110)
        self._zoom.pack(side="right")
        stil.klein(kopf, "Doppelklick vergrößert, Ziehen verschiebt").pack(side="right", padx=12)

        self.flaeche = tk.Canvas(self, background=FELD, highlightthickness=0)
        self.flaeche.grid(row=1, column=0, sticky="nsew")
        self._leiste_y = ctk.CTkScrollbar(self, command=self.flaeche.yview, orientation="vertical")
        self._leiste_x = ctk.CTkScrollbar(self, command=self.flaeche.xview, orientation="horizontal")
        self.flaeche.configure(xscrollcommand=self._leiste_x.set, yscrollcommand=self._leiste_y.set)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.flaeche.bind("<Configure>", self._groesse_geaendert)
        self.flaeche.bind("<ButtonPress-1>", lambda e: self.flaeche.scan_mark(e.x, e.y))
        self.flaeche.bind("<B1-Motion>", lambda e: self.flaeche.scan_dragto(e.x, e.y, gain=1))
        self.flaeche.bind("<Double-Button-1>", self.umschalten)

    def zeige(self, dateien: list[Path]) -> None:
        """Bilder neu einlesen; dasselbe Blatt bleibt ausgewählt, wenn es noch da ist."""
        self.dateien = dateien
        for knopf in self._knoepfe.values():
            knopf.destroy()
        self._knoepfe = {}
        for datei in dateien:
            knopf = ctk.CTkButton(self._wahl, text=datei.name, height=40, width=70, corner_radius=20,
                                  font=(self.stil.sans, 14), command=lambda n=datei.name: self.waehle(n))
            knopf.pack(side="left", padx=(0, 6))
            self._knoepfe[datei.name] = knopf
        namen = [d.name for d in dateien]
        self.waehle(self.auswahl if self.auswahl in namen else (namen[0] if namen else ""))

    def waehle(self, name: str) -> None:
        self.auswahl = name
        for n, knopf in self._knoepfe.items():
            aktiv = n == name
            knopf.configure(fg_color=AKZENT if aktiv else FELD, hover_color=AKZENT_DUNKEL if aktiv else TON,
                            text_color="white" if aktiv else TINTE)
        datei = next((d for d in self.dateien if d.name == name), None)
        self._bild = None
        if datei is not None:
            try:
                with Image.open(datei) as bild:
                    self._bild = ImageOps.exif_transpose(bild).convert("RGB")
            except OSError:
                self._bild = None
        self.zeichnen()

    def umschalten(self, ereignis=None) -> None:
        anteil = None
        if ereignis is not None and self._bild is not None:
            x0, y0, massstab = self._versatz
            anteil = ((self.flaeche.canvasx(ereignis.x) - x0) / (self._bild.width * massstab),
                      (self.flaeche.canvasy(ereignis.y) - y0) / (self._bild.height * massstab))
        self.einpassen = not self.einpassen
        self._zoom.configure(text="Volle Größe" if self.einpassen else "Einpassen")
        if self.einpassen:
            self._leiste_y.grid_remove()
            self._leiste_x.grid_remove()
        else:
            self._leiste_y.grid(row=1, column=1, sticky="ns")
            self._leiste_x.grid(row=2, column=0, sticky="ew")
        self.update_idletasks()
        self.zeichnen()
        if anteil and not self.einpassen:
            # die angeklickte Stelle in die Mitte holen
            b, h = self._bild.size
            self.flaeche.xview_moveto(anteil[0] - self.flaeche.winfo_width() / b / 2)
            self.flaeche.yview_moveto(anteil[1] - self.flaeche.winfo_height() / h / 2)

    def zeichnen(self) -> None:
        self.flaeche.delete("all")
        breite, hoehe = max(self.flaeche.winfo_width(), 1), max(self.flaeche.winfo_height(), 1)
        if self._bild is None:
            self.flaeche.configure(scrollregion=(0, 0, breite, hoehe))
            self.flaeche.create_text(breite // 2, hoehe // 2, text=self.leertext, fill=GRAU,
                                     font=(self.stil.sans, 14), width=max(breite - 40, 100), justify="center")
            return
        if self.einpassen:
            massstab = min(breite / self._bild.width, hoehe / self._bild.height, 1.0)
            groesse = (max(1, round(self._bild.width * massstab)), max(1, round(self._bild.height * massstab)))
            self._foto = ImageTk.PhotoImage(self._bild.resize(groesse, Image.LANCZOS))
            x0, y0 = (breite - groesse[0]) // 2, (hoehe - groesse[1]) // 2
            self.flaeche.configure(scrollregion=(0, 0, breite, hoehe))
            self.flaeche.xview_moveto(0)
            self.flaeche.yview_moveto(0)
        else:
            massstab, x0, y0 = 1.0, 0, 0
            self._foto = ImageTk.PhotoImage(self._bild)
            self.flaeche.configure(scrollregion=(0, 0, *self._bild.size))
        self._versatz = (x0, y0, massstab)
        self.flaeche.create_image(x0, y0, image=self._foto, anchor="nw")

    def _groesse_geaendert(self, _ereignis) -> None:
        if self._nachlauf:
            self.after_cancel(self._nachlauf)
        self._nachlauf = self.after(80, self.zeichnen)


class Bogenkarten(ctk.CTkFrame):
    """Die gefundenen Bögen als Karten nebeneinander; die Bilder passen sich dem Platz an."""

    ANZAHL = 3

    def __init__(self, eltern, stil: Stil, leertext: str):
        super().__init__(eltern, fg_color="transparent")
        self.stil = stil
        self._bilder: list[tuple[ctk.CTkImage, tuple[int, int]]] = []
        self._leer = stil.klein(self, leertext)
        self._karten: list[ctk.CTkFrame] = []
        self._nachlauf = None
        self.pack_propagate(False)
        self.grid_propagate(False)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(tuple(range(self.ANZAHL)), weight=1, uniform="bogen")
        self.bind("<Configure>", self._groesse_geaendert)

    def zeige(self, dateien: list[Path]) -> None:
        for karte in self._karten:
            karte.destroy()
        self._karten, self._bilder = [], []
        self._leer.grid_forget()
        if not dateien:
            self._leer.grid(row=0, column=0, columnspan=self.ANZAHL, sticky="nw")
            return
        for spalte, datei in enumerate(dateien[: self.ANZAHL]):
            karte = self.stil.karte(self)
            karte.grid(row=0, column=spalte, sticky="nsew",
                       padx=(0 if spalte == 0 else 8, 0 if spalte == self.ANZAHL - 1 else 8))
            karte.pack_propagate(False)
            bogen = "ABC"[spalte]
            self.stil.klein(karte, f"{datei.name}  ·  Bogen {bogen}").pack(side="bottom", pady=(2, 10))
            try:
                with Image.open(datei) as bild:
                    bild.draft("RGB", (700, 900))  # große JPEGs gleich verkleinert einlesen
                    bild = ImageOps.exif_transpose(bild).convert("RGB")
                    bild.thumbnail((700, 900))
            except OSError:
                self.stil.klein(karte, "Bild nicht lesbar", FARBEN["fehler"]).pack(expand=True)
                self._karten.append(karte)
                continue
            vorschau = ctk.CTkImage(bild, size=(10, 10))
            ctk.CTkLabel(karte, text="", image=vorschau).pack(expand=True, padx=10, pady=(10, 2))
            self._bilder.append((vorschau, bild.size))
            self._karten.append(karte)
        self._groesse_geaendert()

    def _groesse_geaendert(self, _ereignis=None) -> None:
        if self._nachlauf:
            self.after_cancel(self._nachlauf)
        self._nachlauf = self.after(60, self._einpassen)

    def _einpassen(self) -> None:
        skalierung = ctk.ScalingTracker.get_window_scaling(self.winfo_toplevel())
        breite = self.winfo_width() / skalierung / self.ANZAHL - 44
        hoehe = self.winfo_height() / skalierung - 62
        for vorschau, (b, h) in self._bilder:
            massstab = max(0.05, min(breite / b, hoehe / h))
            vorschau.configure(size=(max(1, round(b * massstab)), max(1, round(h * massstab))))


class Oberflaeche:
    def __init__(self, fenster: ctk.CTk):
        ctk.set_appearance_mode("light")
        self.fenster = fenster
        self.stil = Stil(fenster)
        self._temp = tempfile.TemporaryDirectory(prefix="kritzelei-")
        self.temp = Path(self._temp.name)
        self._prozess: subprocess.Popen | None = None
        self._zeilen: queue.Queue = queue.Queue()
        self._danach = None
        self._abgebrochen = False
        self._startknoepfe: list[ctk.CTkButton] = []
        self._proben: dict[tuple[str, int], Path] = {}
        self._otf: Path | None = None
        self._probe_foto = None
        self._nachlaeufe: dict[str, str] = {}
        self._abholen = None
        self._waehler: subprocess.Popen | None = None
        self._aktion: dict[str, ctk.CTkButton] = {}
        self._weiter: dict[str, ctk.CTkButton] = {}
        self.aktuell = SEITEN[0]

        fenster.title("Kritzelei wird Schrift – Starter zur Handschrift-Fontifizierung")
        self._icon = tk.PhotoImage(master=fenster, file=str(BILDER / "icon.png"))
        fenster.iconphoto(True, self._icon)
        breite = min(1160, fenster.winfo_screenwidth() - 40)
        hoehe = min(820, fenster.winfo_screenheight() - 90)
        fenster.geometry(f"{breite}x{hoehe}")
        fenster.minsize(1100, 620)
        fenster.configure(fg_color=PAPIER)
        fenster.protocol("WM_DELETE_WINDOW", self.beenden)

        # Einstellungen; der Ordner der entzerrten Scans gilt für alle Schritte
        self.fotos = tk.StringVar(value="Kritzelei-Bilder-Original")
        self.vorbereitet = tk.StringVar(value="Kritzelei-Bilder-Vorbereitung")
        self.name = tk.StringVar(value="Kritzelei-01")
        self.ziel = tk.StringVar(value="Output/Kritzelei-01")
        self.stift = tk.StringVar(value="standard")
        self.blur = tk.StringVar(value="3")
        self.strichbreite_an = tk.BooleanVar(value=True)
        self.strichbreite_anteil = tk.DoubleVar(value=auftrag.ScanEinstellungen.strichbreite_anteil)
        self.strichbreite = tk.StringVar()
        self.ohne_font = tk.BooleanVar(value=False)
        self.rmppm = tk.BooleanVar(value=True)
        self.rmjpg = tk.BooleanVar(value=False)
        self.rmsvg = tk.BooleanVar(value=False)
        self.sfd_auswahl = tk.StringVar()
        self.schnitt_quelle = tk.StringVar()
        self.schnitt_an = {stil: tk.BooleanVar(value=True) for stil, _ in SCHNITTE}
        self.schnitt_art = tk.StringVar(value="ableiten")
        self.schnitt_staerke = tk.IntVar(value=46)
        self.schnitt_neigung = tk.IntVar(value=12)
        self.export_an = {wert: tk.BooleanVar(value=an) for wert, _, _, an in EXPORT_FORMATE}
        self._export_ort: Path | None = None
        self.probe_groesse = tk.IntVar(value=48)
        self._alter_name = self.name.get()

        fenster.grid_columnconfigure(1, weight=1)
        fenster.grid_rowconfigure(0, weight=1)
        self.knoepfe: dict[str, ctk.CTkButton] = {}
        self._seitenleiste_bauen()
        self.hauptteil = ctk.CTkFrame(fenster, fg_color=PAPIER, corner_radius=0)
        self.hauptteil.grid(row=0, column=1, sticky="nsew")
        self.hauptteil.grid_columnconfigure(0, weight=1)
        self.hauptteil.grid_rowconfigure(0, weight=1)
        self._protokoll_bauen()

        self.seiten: dict[str, ctk.CTkFrame] = {}
        self.zeige("Start")

        self.fotos.trace_add("write", lambda *_: self._spaeter("fotos", self._fotos_aktualisieren))
        self.ziel.trace_add("write", lambda *_: self._spaeter("export", self._export_aktualisieren))
        self.vorbereitet.trace_add("write", lambda *_: self._spaeter("boegen", self._boegen_aktualisieren))
        self.name.trace_add("write", lambda *_: self._name_geaendert())
        self.strichbreite_an.trace_add("write", lambda *_: self._strichbreite_geaendert())
        self.strichbreite_anteil.trace_add("write", lambda *_: self._strichbreite_geaendert())
        self.ohne_font.trace_add("write", lambda *_: self._ohne_font_geaendert())
        self.rmsvg.trace_add("write", lambda *_: self._ohne_font_geaendert())
        self.probe_groesse.trace_add("write", lambda *_: self._probe_groesse_geaendert())

        self._abholen = self.fenster.after(50, self._ausgaben_abholen)

    # --- Aufbau: Rahmen ---------------------------------------------------------

    def _seitenleiste_bauen(self) -> None:
        leiste = ctk.CTkFrame(self.fenster, width=270, corner_radius=0, fg_color=AKZENT)
        leiste.grid(row=0, column=0, sticky="nsew")
        leiste.grid_propagate(False)
        leiste.grid_columnconfigure(0, weight=1)
        leiste.grid_rowconfigure(2, weight=1)

        with Image.open(BILDER / "titel.png") as bild:
            titel = ctk.CTkImage(bild.copy(), size=(bild.width // 2, bild.height // 2))
        ctk.CTkLabel(leiste, text="", image=titel, anchor="w").grid(row=0, column=0, sticky="w", padx=28, pady=(36, 30))

        nav = ctk.CTkFrame(leiste, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="ew", padx=14)
        nav.grid_columnconfigure(0, weight=1)
        for zeile, name in enumerate(SEITEN):
            text = name if zeile == 0 else f"{zeile}    {name}"
            knopf = ctk.CTkButton(nav, text=text, anchor="w", height=44, corner_radius=12,
                                  font=(self.stil.sans, 15), fg_color="transparent", hover_color=AKZENT_HELL,
                                  text_color="white", command=lambda n=name: self.zeige(n))
            knopf.grid(row=zeile, column=0, sticky="ew", pady=2)
            self.knoepfe[name] = knopf

        unten = ctk.CTkFrame(leiste, fg_color="transparent")
        unten.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        unten.grid_columnconfigure(0, weight=1)
        info = ctk.CTkButton(unten, text="Info", anchor="w", height=40, corner_radius=12, font=(self.stil.sans, 15),
                             fg_color="transparent", hover_color=AKZENT_HELL, text_color="white",
                             command=lambda: self.zeige("Info"))
        info.grid(row=0, column=0, sticky="ew")
        self.knoepfe["Info"] = info

    def _protokoll_bauen(self) -> None:
        rahmen = ctk.CTkFrame(self.hauptteil, fg_color="transparent")
        rahmen.grid(row=1, column=0, sticky="ew", padx=PLATZ, pady=(0, 14))
        rahmen.grid_columnconfigure(0, weight=1)

        kopf = ctk.CTkFrame(rahmen, fg_color="transparent")
        kopf.grid(row=0, column=0, sticky="ew")
        self.protokoll_knopf = ctk.CTkButton(kopf, text="▸  Protokoll anzeigen", fg_color="transparent",
                                             hover_color=TON, text_color=GRAU, font=(self.stil.sans, 13),
                                             width=160, anchor="w", command=self.protokoll_umschalten)
        self.protokoll_knopf.pack(side="left")
        self.status = self.stil.klein(kopf, "Bereit.")
        self.status.pack(side="left", padx=10)
        self.abbruch = self.stil.neben(kopf, "Abbrechen", self.abbrechen, hoehe=30, breite=90)
        self.fortschritt = ctk.CTkProgressBar(kopf, mode="indeterminate", width=150, height=8,
                                              progress_color=AKZENT, fg_color=TON)

        self._protokoll_rahmen = rahmen
        self.protokoll: ctk.CTkTextbox | None = None  # entsteht erst beim ersten Öffnen
        self._protokoll_puffer: list[tuple[str, str | None]] = []
        self._protokoll_offen = False

    def _protokoll_anlegen(self) -> None:
        self.protokoll = ctk.CTkTextbox(self._protokoll_rahmen, height=170, wrap="word", state="disabled",
                                        corner_radius=12, fg_color=KARTE, text_color=TINTE, border_width=1,
                                        border_color=LINIE, scrollbar_button_color=LINIE,
                                        scrollbar_button_hover_color="#CFCDC4", font=(self.stil.mono, 12))
        self.protokoll.tag_config("befehl", foreground=AKZENT)
        self.protokoll.tag_config("warnung", foreground=FARBEN["warnung"])
        self.protokoll.tag_config("fehler", foreground=FARBEN["fehler"])
        puffer, self._protokoll_puffer = self._protokoll_puffer, []
        for zeile, art in puffer:
            self._protokollieren(zeile, art)

    def protokoll_umschalten(self, offen: bool | None = None) -> None:
        self._protokoll_offen = (not self._protokoll_offen) if offen is None else offen
        if self._protokoll_offen:
            if self.protokoll is None:
                self._protokoll_anlegen()
            self.protokoll.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            self.protokoll_knopf.configure(text="▾  Protokoll ausblenden")
            self.protokoll.see("end")
        else:
            self.protokoll.grid_forget()
            self.protokoll_knopf.configure(text="▸  Protokoll anzeigen")

    def _neue_seite(self, titel: str, einleitung: str = "", rollbar: bool = False):
        """Seite mit Überschrift; gibt (Seite, Inhalt, Fußzeile) zurück."""
        seite = ctk.CTkFrame(self.hauptteil, fg_color=PAPIER, corner_radius=0)
        fuss = ctk.CTkFrame(seite, fg_color="transparent")
        fuss.pack(side="bottom", fill="x", padx=PLATZ, pady=(10, 8))
        if rollbar:
            rolle = Rollflaeche(seite)
            rolle.pack(fill="both", expand=True, padx=PLATZ, pady=(34, 0))
            inhalt = rolle.inhalt
        else:
            inhalt = ctk.CTkFrame(seite, fg_color="transparent")
            inhalt.pack(fill="both", expand=True, padx=PLATZ, pady=(34, 0))
        self.stil.h1(inhalt, titel).pack(anchor="w")
        if einleitung:
            text = self.stil.text(inhalt, einleitung, breite=560, groesse=15)
            text.pack(anchor="w", pady=(8, 18))
            self._mitwachsen(text, inhalt, hoechstens=760)
        return seite, inhalt, fuss

    def _mitwachsen(self, text: ctk.CTkLabel, behaelter, abzug: int = 0, hoechstens: int = 2000) -> None:
        """Zeilenumbruch an die Breite des Behälters koppeln; feste Breiten sprengen schmale Fenster."""

        def anpassen(ereignis) -> None:
            skalierung = ctk.ScalingTracker.get_window_scaling(self.fenster)
            text.configure(wraplength=int(min(hoechstens, max(160, ereignis.width / skalierung - abzug))))

        behaelter.bind("<Configure>", anpassen, add="+")

    def _ordnerfeld(self, eltern, titel: str, variable: tk.StringVar) -> ctk.CTkFrame:
        rahmen = ctk.CTkFrame(eltern, fg_color="transparent")
        self.stil.fett(rahmen, titel).pack(anchor="w", pady=(0, 5))
        zeile = ctk.CTkFrame(rahmen, fg_color="transparent")
        zeile.pack(fill="x")
        self.stil.feld(zeile, variable).pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.stil.neben(zeile, "Wählen …", lambda: self._ordner_waehlen(variable, titel)).pack(side="right")
        return rahmen

    def _ordner_waehlen(self, variable: tk.StringVar, titel: str) -> None:
        start = pfad(variable.get())
        gewaehlt = self._waehlen(titel, start if start.is_dir() else auftrag.WURZEL)
        if gewaehlt:
            try:
                variable.set(str(Path(gewaehlt).relative_to(auftrag.WURZEL)))
            except ValueError:
                variable.set(gewaehlt)

    def _waehlen(self, titel: str, start: Path, nur_sfd: bool = False) -> str | None:
        """Ordner oder sfd-Datei wählen: mit dem Dialog des Desktops, sonst notfalls mit dem von Tk."""
        if self._waehler is not None:
            return None
        befehl = auftrag.befehl_waehler(titel, start, nur_sfd, int(self.fenster.wm_frame(), 16))
        if befehl is None:
            if nur_sfd:
                return filedialog.askopenfilename(parent=self.fenster, title=titel, initialdir=str(start),
                                                  filetypes=[("FontForge-Dateien", "*.sfd")]) or None
            return filedialog.askdirectory(parent=self.fenster, title=titel, initialdir=str(start)) or None
        return self._dialog_ausfuehren(befehl)

    def _speichern_unter(self, titel: str, vorschlag: Path) -> str | None:
        if self._waehler is not None:
            return None
        befehl = auftrag.befehl_speichern_unter(titel, vorschlag, int(self.fenster.wm_frame(), 16))
        if befehl is None:
            return filedialog.asksaveasfilename(parent=self.fenster, title=titel, initialdir=str(vorschlag.parent),
                                                initialfile=vorschlag.name, defaultextension=".zip",
                                                filetypes=[("ZIP-Archive", "*.zip")]) or None
        return self._dialog_ausfuehren(befehl)

    def _dialog_ausfuehren(self, befehl: list[str]) -> str | None:
        self._waehler = subprocess.Popen(befehl, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        fertig = tk.BooleanVar(master=self.fenster, value=False)

        def pruefen() -> None:
            # warten, ohne dass das Fenster einfriert und der Desktop es für abgestürzt hält
            if self._waehler is None or self._waehler.poll() is not None:
                fertig.set(True)
            else:
                self.fenster.after(50, pruefen)

        pruefen()
        self.fenster.wait_variable(fertig)
        prozess, self._waehler = self._waehler, None
        if prozess is None or prozess.returncode != 0:
            return None
        return prozess.stdout.read().strip() or None

    def _frage(self, titel: str, text: str, ja: str = "Ja", nein: str = "Abbrechen") -> bool:
        return Dialog(self.fenster, self.stil, titel, text, ja, nein).warten()

    def _fehler(self, titel: str, text: str) -> None:
        Dialog(self.fenster, self.stil, titel, text, "Verstanden").warten()

    def _schritt_knoepfe(self, seite: str, fuss, aktion: ctk.CTkButton, weiter_text: str, ziel: str) -> None:
        """Regel für alle Seiten: Aktionen bleiben auf der Seite, nur Knöpfe mit Pfeil wechseln sie."""
        self._aktion[seite] = self._startknopf(aktion)
        self._weiter[seite] = self.stil.haupt(fuss, f"{weiter_text}  →", lambda: self.zeige(ziel))
        aktion.pack(side="right")

    def _schritt_stand(self, seite: str, erledigt: bool) -> None:
        """Nach einem erfolgreichen Schritt wird „Weiter“ zum Hauptknopf."""
        if seite not in self._aktion:
            return
        aktion, weiter = self._aktion[seite], self._weiter[seite]
        aktion.pack_forget()
        weiter.pack_forget()
        if erledigt:
            self.stil.als_neben(aktion)
            weiter.pack(side="right")
            aktion.pack(side="right", padx=(0, 10))
        else:
            self.stil.als_haupt(aktion)
            aktion.pack(side="right")

    def _startknopf(self, knopf: ctk.CTkButton) -> ctk.CTkButton:
        self._startknoepfe.append(knopf)
        return knopf

    def _seite_bauen(self, name: str) -> None:
        """Jede Seite entsteht erst beim ersten Öffnen: Der Aufbau aller Seiten dauert viele Sekunden,
        weil CustomTkinter beim Zeichnen jeder Bildlaufleiste das ganze Layout neu berechnet."""
        bauen, einrichten = {
            "Start": (self._seite_start, ()),
            "Entzerren": (self._seite_entzerren, (self._fotos_aktualisieren,)),
            "Erkennung prüfen": (self._seite_pruefen, (self._boegen_aktualisieren,)),
            "Schrift erzeugen": (self._seite_erzeugen, (self._quelle_anzeigen, self._strichbreite_geaendert,
                                                        self._ohne_font_geaendert)),
            "Ergebnis": (self._seite_ergebnis, ()),
            "Schriftschnitte": (self._seite_schnitte, (self._schnitt_art_geaendert,)),
            "Export": (self._seite_export, ()),
            "Info": (self._seite_info, ()),
        }[name]
        self.seiten[name] = bauen()
        for aufgabe in einrichten:
            aufgabe()

    def _gebaut(self, name: str) -> bool:
        return name in self.seiten

    def zeige(self, name: str) -> None:
        if not self._gebaut(name):
            self._seite_bauen(name)
        for seite in self.seiten.values():
            seite.grid_forget()
        self.seiten[name].grid(row=0, column=0, sticky="nsew")
        self.aktuell = name
        for n, knopf in self.knoepfe.items():
            aktiv = n == name
            knopf.configure(fg_color=PAPIER if aktiv else "transparent",
                            hover_color=PAPIER if aktiv else AKZENT_HELL,
                            text_color=AKZENT if aktiv else "white",
                            font=(self.stil.sans, 15, "bold" if aktiv else "normal"))
        if name == "Ergebnis":
            self.ergebnis_aktualisieren()
        elif name == "Schriftschnitte":
            self._schnitt_quelle_vorschlagen()
        elif name == "Export":
            self._export_aktualisieren()

    # --- Aufbau: Seiten ---------------------------------------------------------

    def _seite_start(self) -> ctk.CTkFrame:
        s = self.stil
        seite, inhalt, fuss = self._neue_seite(
            "Aus Ihrer Handschrift wird eine Schrift",
            "Sie füllen drei Bögen von Hand aus, fotografieren oder scannen sie, und dieses Programm macht daraus "
            "eine Schriftdatei, die Sie in FontForge weiter verfeinern können.", rollbar=True)

        probe = s.karte(inhalt)
        probe.pack(fill="x")
        with Image.open(BILDER / "schriftprobe.png") as bild:
            verhaeltnis = bild.height / bild.width
            muster = ctk.CTkImage(bild.copy(), size=(540, round(540 * verhaeltnis)))

        def anpassen(ereignis) -> None:
            skalierung = ctk.ScalingTracker.get_window_scaling(self.fenster)
            b = min(695, max(200, ereignis.width / skalierung - 56))
            muster.configure(size=(round(b), round(b * verhaeltnis)))

        probe.bind("<Configure>", anpassen)
        ctk.CTkLabel(probe, text="", image=muster, anchor="w").pack(anchor="w", padx=26, pady=(20, 2))
        s.text(probe, "So kann das aussehen: der Beispiel-Font dieses Projekts.", groesse=12, farbe=GRAU).pack(
            anchor="w", padx=26, pady=(0, 14))

        spalten = ctk.CTkFrame(inhalt, fg_color="transparent")
        spalten.pack(fill="x", pady=(22, 0))
        spalten.grid_columnconfigure(0, weight=5, uniform="s")
        spalten.grid_columnconfigure(1, weight=4, uniform="s")

        links = ctk.CTkFrame(spalten, fg_color="transparent")
        links.grid(row=0, column=0, sticky="new", padx=(0, 26))
        s.h2(links, "So geht es").pack(anchor="w", pady=(0, 8))
        kreis = _kreis(TON)
        for nummer, (titel, text) in enumerate([
            ("Entzerren", "Die Bilder werden an den Randmarken gerade gerückt."),
            ("Erkennung prüfen", "Sie sehen, ob alle Kästchen richtig gefunden wurden."),
            ("Schrift erzeugen", "Aus jedem Kästchen wird ein Zeichen der Schrift."),
            ("Ergebnis ansehen", "Eigenen Text ausprobieren und in FontForge überarbeiten."),
            ("Schriftschnitte", "Aus der überarbeiteten Datei Italic, Bold und Bold-Italic ableiten."),
            ("Export", "Andere Formate erzeugen und alles als ZIP zum Weitergeben speichern."),
        ], 1):
            zeile = ctk.CTkFrame(links, fg_color="transparent")
            zeile.pack(fill="x", pady=4)
            ctk.CTkLabel(zeile, text=str(nummer), image=kreis, compound="center", width=30, height=30,
                         text_color=AKZENT, font=(s.sans, 14, "bold")).pack(side="left", anchor="n", padx=(0, 12))
            spalte = ctk.CTkFrame(zeile, fg_color="transparent")
            spalte.pack(side="left", fill="x")
            s.fett(spalte, titel).pack(anchor="w")
            erklaerung = s.text(spalte, text, breite=240, groesse=13, farbe=GRAU)
            erklaerung.pack(anchor="w")
            self._mitwachsen(erklaerung, links, abzug=44)

        rechts = s.karte(spalten)
        rechts.grid(row=0, column=1, sticky="new")
        s.h2(rechts, "Das brauchen Sie").pack(anchor="w", padx=22, pady=(16, 6))
        for text in ("Drei ausgefüllte Bögen der Zeichenvorlage",
                     "Von jedem Bogen ein Foto oder einen Scan, auf dem alle vier Randmarken zu sehen sind",
                     "Dateinamen in der Reihenfolge der Bögen, am besten A, B und C"):
            punkt = ctk.CTkFrame(rechts, fg_color="transparent")
            punkt.pack(anchor="w", fill="x", padx=22, pady=3)
            # gleiche Schrift, Höhe nur so groß wie nötig: So liegt der Punkt auf der Mitte der ersten Zeile.
            ctk.CTkLabel(punkt, text="•", font=(s.serif, 13), text_color=AKZENT, width=14, height=1).pack(
                side="left", anchor="n")
            aufzaehlung = s.text(punkt, text, breite=220, groesse=13)
            aufzaehlung.configure(height=1)
            aufzaehlung.pack(side="left", anchor="n", padx=(2, 0))
            self._mitwachsen(aufzaehlung, rechts, abzug=66)
        vorlage = s.neben(rechts, "Zeichenvorlage öffnen", self.vorlage_oeffnen, hoehe=40, breite=170)
        vorlage.pack(anchor="w", padx=22, pady=(10, 18))
        if not (shutil.which("xdg-open") and ZEICHENVORLAGE.is_file()):
            vorlage.configure(state="disabled")

        s.haupt(fuss, "Los geht's  →", lambda: self.zeige("Entzerren")).pack(side="right")
        return seite

    def _seite_entzerren(self) -> ctk.CTkFrame:
        s = self.stil
        seite, inhalt, fuss = self._neue_seite(
            "Scans entzerren",
            "Die Fotos oder Scans der ausgefüllten Bögen werden anhand der vier Randmarken gerade gerückt "
            "und zugeschnitten.")

        felder = ctk.CTkFrame(inhalt, fg_color="transparent")
        felder.pack(fill="x")
        felder.grid_columnconfigure((0, 1), weight=1, uniform="f")
        self._ordnerfeld(felder, f"Ordner der originalen Scans ({auftrag.BILD_ARTEN})", self.fotos).grid(
            row=0, column=0, sticky="ew", padx=(0, 12))
        self._ordnerfeld(felder, "Zielordner der entzerrten Scans", self.vorbereitet).grid(
            row=0, column=1, sticky="ew", padx=(12, 0))

        kopf = ctk.CTkFrame(inhalt, fg_color="transparent")
        kopf.pack(fill="x", pady=(18, 8))
        s.h2(kopf, "Gefundene Bögen").pack(side="left")
        self.fotos_info = s.klein(kopf, breite=560)
        self.fotos_info.pack(side="left", padx=12)

        self.fotos_ansicht = Bogenkarten(inhalt, s, "Hier erscheinen die Scans aus dem gewählten Ordner.")
        self.fotos_ansicht.pack(fill="both", expand=True)

        self._schritt_knoepfe("Entzerren", fuss, s.haupt(fuss, "Scans entzerren", self.fotos_entzerren),
                              "Weiter: Erkennung prüfen", "Erkennung prüfen")
        return seite

    def _seite_pruefen(self) -> ctk.CTkFrame:
        s = self.stil
        seite, inhalt, fuss = self._neue_seite("Erkennung prüfen")
        inhalt.pack_configure(pady=(34, 0))

        self._ordnerfeld(inhalt, "Ordner der entzerrten Scans", self.vorbereitet).pack(fill="x", pady=(12, 10))

        legende = ctk.CTkFrame(inhalt, fg_color="transparent")
        legende.pack(anchor="w", pady=(0, 10))
        for farbe, text in LEGENDE:
            ctk.CTkLabel(legende, text="■", text_color=farbe, font=(s.sans, 13), width=14).pack(side="left")
            s.klein(legende, text).pack(side="left", padx=(4, 16))

        self.pruef_ansicht = Bildansicht(inhalt, s, "Hier erscheinen die Bögen mit den erkannten Kästchen.")
        self.pruef_ansicht.pack(fill="both", expand=True)

        self.pruef_info = s.klein(fuss, "Noch nicht geprüft.", breite=520)
        self.pruef_info.pack(side="left")
        self._schritt_knoepfe("Erkennung prüfen", fuss, s.haupt(fuss, "Erkennung prüfen", self.erkennung_pruefen),
                              "Weiter: Schrift erzeugen", "Schrift erzeugen")
        return seite

    def _seite_erzeugen(self) -> ctk.CTkFrame:
        s = self.stil
        seite, inhalt, fuss = self._neue_seite("Schrift erzeugen", rollbar=True)

        schrift = ctk.CTkFrame(inhalt, fg_color="transparent")
        schrift.pack(fill="x", pady=(14, 0))
        schrift.grid_columnconfigure((0, 1), weight=1, uniform="f")
        name = ctk.CTkFrame(schrift, fg_color="transparent")
        name.grid(row=0, column=0, sticky="new", padx=(0, 12))
        s.fett(name, "Name der Schriftfamilie").pack(anchor="w", pady=(0, 5))
        s.feld(name, self.name).pack(fill="x")
        self._ordnerfeld(schrift, "Zielordner", self.ziel).grid(row=0, column=1, sticky="new", padx=(12, 0))
        self.quelle_info = s.klein(inhalt, breite=560)
        self.quelle_info.pack(anchor="w", pady=(8, 14))
        self._mitwachsen(self.quelle_info, inhalt)

        raster = ctk.CTkFrame(inhalt, fg_color="transparent")
        raster.pack(fill="x")
        raster.grid_columnconfigure((0, 1), weight=1, uniform="k")

        stift = s.karte(raster)
        stift.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 16))
        s.h2(stift, "Stift").pack(anchor="w", padx=20, pady=(14, 6))
        for wert, text in auftrag.STIFT_AUSWAHL.items():
            ctk.CTkRadioButton(stift, text=text, value=wert, variable=self.stift, font=(s.sans, 14),
                               text_color=TINTE, fg_color=AKZENT, hover_color=AKZENT_DUNKEL, border_color="#B8B8C8",
                               radiobutton_width=18, radiobutton_height=18).pack(anchor="w", padx=20, pady=3)
        blur = ctk.CTkFrame(stift, fg_color="transparent")
        blur.pack(anchor="w", padx=20, pady=(8, 14))
        s.klein(blur, "Weichzeichner", TINTE).pack(side="left")
        ctk.CTkOptionMenu(blur, values=["0", "1", "3", "5", "7", "9"], variable=self.blur, width=70, height=30,
                          corner_radius=10, fg_color=FELD, button_color=FELD, button_hover_color=TON,
                          text_color=TINTE, font=(s.sans, 14), dropdown_font=(s.sans, 14)).pack(side="left", padx=8)
        s.klein(blur, "0 = aus").pack(side="left")

        breite = s.karte(raster)
        breite.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 16))
        s.h2(breite, "Strichbreite").pack(anchor="w", padx=20, pady=(14, 6))
        s.haken(breite, "Strichbreiten einander annähern", self.strichbreite_an).pack(anchor="w", padx=20)
        regler = ctk.CTkFrame(breite, fg_color="transparent")
        regler.pack(fill="x", padx=20, pady=(10, 6))
        s.klein(regler, "Stärke", TINTE).pack(side="left")
        self.strichbreite_wert = s.klein(regler, "", TINTE)
        self.strichbreite_wert.configure(width=44)
        self.strichbreite_wert.pack(side="right")
        self.strichbreite_regler = ctk.CTkSlider(regler, from_=0.1, to=1.0, number_of_steps=18, height=16,
                                                 variable=self.strichbreite_anteil, progress_color=AKZENT,
                                                 button_color=AKZENT, button_hover_color=AKZENT_DUNKEL, fg_color=TON)
        self.strichbreite_regler.pack(side="left", fill="x", expand=True, padx=10)
        ziel = ctk.CTkFrame(breite, fg_color="transparent")
        ziel.pack(anchor="w", padx=20)
        s.klein(ziel, "Zielbreite", TINTE).pack(side="left")
        self.strichbreite_feld = ctk.CTkEntry(ziel, textvariable=self.strichbreite, width=76, height=34, corner_radius=10,
                                              border_width=0, fg_color=FELD, text_color=TINTE, font=(s.sans, 14))
        self.strichbreite_feld.pack(side="left", padx=8)
        s.klein(ziel, "optional").pack(side="left")
        s.klein(breite, "Font-Einheiten; leer = Median aller Zeichen").pack(anchor="w", padx=20, pady=(4, 14))

        zusaetze = s.karte(raster)
        zusaetze.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        s.h2(zusaetze, "Zusätze").pack(anchor="w", padx=20, pady=(14, 8))
        self.ohne_font_feld = s.haken(zusaetze, "Nur SVG-Dateien erzeugen, keinen Font", self.ohne_font)
        self.ohne_font_feld.pack(anchor="w", padx=20, pady=(0, 16))

        aufraeumen = s.karte(raster)
        aufraeumen.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        s.h2(aufraeumen, "Zwischendateien am Ende löschen").pack(anchor="w", padx=20, pady=(14, 8))
        haken = ctk.CTkFrame(aufraeumen, fg_color="transparent")
        haken.pack(anchor="w", padx=20, pady=(0, 16))
        s.haken(haken, "PPM", self.rmppm).pack(side="left", padx=(0, 14))
        s.haken(haken, "JPG", self.rmjpg).pack(side="left", padx=(0, 14))
        self.rmsvg_feld = s.haken(haken, "SVG", self.rmsvg)
        self.rmsvg_feld.pack(side="left")

        self._startknopf(s.neben(fuss, "Nur Font aus vorhandenen SVG-Dateien", self.font_aus_svg, hoehe=44, breite=290)).pack(
            side="left")
        self._schritt_knoepfe("Schrift erzeugen", fuss, s.haupt(fuss, "Schrift erzeugen", self.schrift_erzeugen),
                              "Weiter: Ergebnis ansehen", "Ergebnis")
        return seite

    def _seite_ergebnis(self) -> ctk.CTkFrame:
        s = self.stil
        seite, inhalt, fuss = self._neue_seite("Ergebnis")

        self.ergebnis_info = s.klein(inhalt, "Hier erscheint die Schrift, sobald sie erzeugt ist.", breite=640)
        self.ergebnis_info.pack(anchor="w", pady=(4, 12))

        eingabe = ctk.CTkFrame(inhalt, fg_color="transparent")
        eingabe.pack(fill="x", pady=(0, 10))
        self.probe_text = ctk.CTkTextbox(eingabe, height=78, wrap="word", corner_radius=12, fg_color=FELD,
                                         text_color=TINTE, font=(s.sans, 14), border_width=0,
                                         scrollbar_button_color=LINIE, scrollbar_button_hover_color="#CFCDC4")
        self.probe_text.insert("1.0", SCHRIFTPROBE_TEXT)
        self.probe_text.pack(side="left", fill="x", expand=True)
        self.probe_text.bind("<KeyRelease>", lambda _: self._spaeter("probe", self.probe_setzen))
        groesse = ctk.CTkFrame(eingabe, fg_color="transparent")
        groesse.pack(side="left", padx=(16, 0))
        self.probe_groesse_text = s.fett(groesse, f"Schriftgröße {self.probe_groesse.get()}")
        self.probe_groesse_text.pack(anchor="w")
        ctk.CTkSlider(groesse, from_=12, to=120, number_of_steps=27, width=150, height=16, variable=self.probe_groesse,
                      progress_color=AKZENT, button_color=AKZENT, button_hover_color=AKZENT_DUNKEL, fg_color=TON).pack(
            pady=(8, 0))

        karte = s.karte(inhalt)
        karte.pack(fill="both", expand=True)
        self.probe_flaeche = tk.Canvas(karte, background="white", highlightthickness=0)
        leiste = ctk.CTkScrollbar(karte, command=self.probe_flaeche.yview, button_color=LINIE,
                                  button_hover_color="#CFCDC4")
        self.probe_flaeche.configure(yscrollcommand=leiste.set)
        leiste.pack(side="right", fill="y", padx=(0, 4), pady=8)
        self.probe_flaeche.pack(side="left", fill="both", expand=True, padx=(10, 2), pady=10)
        self.probe_flaeche.bind("<Configure>", lambda _: self._spaeter("probe", self.probe_setzen))

        self.sfd_menue = ctk.CTkOptionMenu(fuss, values=[""], width=170, height=34, corner_radius=10, fg_color=FELD,
                                           button_color=FELD, button_hover_color=TON, text_color=TINTE,
                                           font=(s.sans, 14), dropdown_font=(s.sans, 14), command=self._sfd_gewaehlt)
        self.sfd_menue.pack(side="left")
        self.ordner_knopf = s.neben(fuss, "Ordner öffnen", self.ordner_oeffnen, hoehe=44, breite=130)
        self.ordner_knopf.pack(side="left", padx=10)
        self.ergebnis_weiter = s.neben(fuss, "Weiter: Schriftschnitte  →", lambda: self.zeige("Schriftschnitte"),
                                       hoehe=44, breite=190)
        self.ergebnis_weiter.pack(side="right")
        self.fontforge_knopf = s.haupt(fuss, "In FontForge öffnen", self.in_fontforge_oeffnen)
        self.fontforge_knopf.pack(side="right", padx=(0, 10))
        return seite

    def _seite_schnitte(self) -> ctk.CTkFrame:
        s = self.stil
        seite, inhalt, fuss = self._neue_seite(
            "Schriftschnitte",
            "Überarbeiten Sie zuerst die Regular-Datei in FontForge und speichern Sie sie. Erst danach entstehen hier "
            "die weiteren Schnitte, so fällt jede Korrektur nur einmal an.", rollbar=True)

        s.fett(inhalt, "Überarbeitete Regular-Datei (*.sfd)").pack(anchor="w", pady=(0, 5))
        zeile = ctk.CTkFrame(inhalt, fg_color="transparent")
        zeile.pack(fill="x", pady=(0, 16))
        s.feld(zeile, self.schnitt_quelle).pack(side="left", fill="x", expand=True, padx=(0, 10))
        s.neben(zeile, "Wählen …", self._schnitt_quelle_waehlen).pack(side="right")

        raster = ctk.CTkFrame(inhalt, fg_color="transparent")
        raster.pack(fill="x")
        raster.grid_columnconfigure((0, 1), weight=1, uniform="k")

        welche = s.karte(raster)
        welche.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        s.h2(welche, "Schnitte").pack(anchor="w", padx=20, pady=(14, 8))
        haken = ctk.CTkFrame(welche, fg_color="transparent")
        haken.pack(anchor="w", padx=20, pady=(0, 12))
        for stil, text in SCHNITTE:
            s.haken(haken, text, self.schnitt_an[stil]).pack(side="left", padx=(0, 14))
        for wert, text in (("ableiten", "Umrisse automatisch ableiten"),
                           ("kennzeichen", "Nur Metainformationen setzen, Umrisse bleiben")):
            ctk.CTkRadioButton(welche, text=text, value=wert, variable=self.schnitt_art, font=(s.sans, 14),
                               text_color=TINTE, fg_color=AKZENT, hover_color=AKZENT_DUNKEL, border_color="#B8B8C8",
                               radiobutton_width=18, radiobutton_height=18,
                               command=self._schnitt_art_geaendert).pack(anchor="w", padx=20, pady=3)
        self.schnitt_art_info = s.klein(welche, breite=280)
        self.schnitt_art_info.pack(anchor="w", padx=20, pady=(6, 14))
        self._mitwachsen(self.schnitt_art_info, welche, abzug=40)

        fein = s.karte(raster)
        fein.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        s.h2(fein, "Einstellungen").pack(anchor="w", padx=20, pady=(14, 8))

        def regler(titel, variable, von, bis, schritte, einheit):
            zeile = ctk.CTkFrame(fein, fg_color="transparent")
            zeile.pack(fill="x", padx=20, pady=(4, 8))
            s.klein(zeile, titel, TINTE).pack(side="left")
            wert = s.klein(zeile, f"{variable.get()}{einheit}", TINTE)
            wert.configure(width=44)
            wert.pack(side="right")
            feld = ctk.CTkSlider(zeile, from_=von, to=bis, number_of_steps=schritte, height=16, variable=variable,
                                 progress_color=AKZENT, button_color=AKZENT, button_hover_color=AKZENT_DUNKEL,
                                 fg_color=TON)
            feld.pack(side="left", fill="x", expand=True, padx=10)
            variable.trace_add("write", lambda *_: wert.configure(text=f"{variable.get()}{einheit}"))
            return feld

        self.schnitt_staerke_regler = regler("Fett", self.schnitt_staerke, 10, 100, 18, "")
        regler("Neigung", self.schnitt_neigung, 4, 24, 20, "°")
        hinweis = s.klein(fein, "Kursiv kommt zur Neigung der Regular-Datei hinzu. Das Kerning wird übernommen und "
                                "sollte geprüft werden.", breite=280)
        hinweis.pack(anchor="w", padx=20, pady=(6, 14))
        self._mitwachsen(hinweis, fein, abzug=40)

        self.schnitt_info = s.klein(fuss, breite=480)
        self.schnitt_info.pack(side="left")
        self._schritt_knoepfe("Schriftschnitte", fuss, s.haupt(fuss, "Schnitte erzeugen", self.schnitte_erzeugen),
                              "Ergebnis ansehen", "Ergebnis")
        return seite

    def _link(self, eltern, text: str, adresse: str) -> ctk.CTkLabel:
        link = ctk.CTkLabel(eltern, text=text, font=(self.stil.sans, 14, "underline"), text_color=AKZENT, anchor="w",
                            cursor="hand2", height=24, corner_radius=EINZUG_TEXT)
        link.bind("<Button-1>", lambda _: self.link_oeffnen(adresse))
        return link

    def link_oeffnen(self, adresse: str) -> None:
        if not webbrowser.open(adresse):
            self._fehler("Link öffnen", f"Der Browser ließ sich nicht öffnen. Die Adresse lautet:\n{adresse}")

    def _seite_info(self) -> ctk.CTkFrame:
        s = self.stil
        seite, inhalt, _fuss = self._neue_seite(
            "Info", "Von handgekritzelten Zeichen zum weiterbearbeitbaren Font: Kritzelei wird Schrift macht aus "
                    "ausgefüllten Bögen eine eigene Schrift, die sich in FontForge weiter verfeinern lässt.", rollbar=True)

        raster = ctk.CTkFrame(inhalt, fg_color="transparent")
        raster.pack(fill="x")
        raster.grid_columnconfigure((0, 1), weight=1, uniform="k")

        projekt = s.karte(raster)
        projekt.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        s.h2(projekt, "Das Projekt").pack(anchor="w", padx=20, pady=(14, 8))
        ctk.CTkLabel(projekt, text=AUTOR, font=(s.sans, 15, "bold"), text_color=TINTE, anchor="w", height=22,
                     corner_radius=EINZUG_TEXT).pack(
            anchor="w", padx=20, pady=(0, 6))
        for nummer, (text, adresse) in enumerate(LINKS, 1):
            self._link(projekt, text, adresse).pack(anchor="w", padx=20, pady=(2, 14 if nummer == len(LINKS) else 2))

        recht = s.karte(raster)
        recht.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        s.h2(recht, "Lizenz").pack(anchor="w", padx=20, pady=(14, 8))
        self._link(recht, *LIZENZ).pack(anchor="w", padx=20, pady=(0, 6))
        hinweis = s.klein(recht, "Für die Oberfläche und die Umwandlung kommen FontForge, potrace, OpenCV, "
                                 "scikit-image, Pillow, fontTools und CustomTkinter zum Einsatz.", breite=280)
        hinweis.pack(anchor="w", padx=20, pady=(4, 14))
        self._mitwachsen(hinweis, recht, abzug=40)
        return seite

    def _seite_export(self) -> ctk.CTkFrame:
        s = self.stil
        seite, inhalt, fuss = self._neue_seite(
            "Export",
            "Erzeugt aus allen Schriftdateien des Ordners weitere Formate. Das ZIP enthält dazu die sfd-Dateien und "
            "einen Hinweistext, aber keine Zwischendateien, und passt gut in eine E-Mail.", rollbar=True)

        self._ordnerfeld(inhalt, "Ordner mit den Schriftdateien", self.ziel).pack(fill="x")
        self.export_info = s.klein(inhalt, breite=560)
        self.export_info.pack(anchor="w", pady=(8, 14))
        self._mitwachsen(self.export_info, inhalt)

        karte = s.karte(inhalt)
        karte.pack(fill="x")
        s.h2(karte, "Formate").pack(anchor="w", padx=20, pady=(14, 8))
        for wert, name, zweck, _an in EXPORT_FORMATE:
            zeile = ctk.CTkFrame(karte, fg_color="transparent")
            zeile.pack(fill="x", padx=20, pady=3)
            haken = s.haken(zeile, name, self.export_an[wert])
            haken.configure(width=90)
            haken.pack(side="left")
            s.klein(zeile, zweck).pack(side="left", padx=(8, 0))
        s.klein(karte, "Die sfd-Dateien für FontForge sind im ZIP immer dabei.").pack(anchor="w", padx=20, pady=(8, 14))

        self.export_bericht = s.klein(inhalt, breite=560)
        self.export_bericht.pack(anchor="w", pady=(12, 0))
        self._mitwachsen(self.export_bericht, inhalt)

        self.export_ordner_knopf = s.neben(fuss, "Ordner öffnen", self.export_ordner_oeffnen, hoehe=44, breite=130)
        self.export_ordner_knopf.pack(side="left")
        if not shutil.which("xdg-open"):
            self.export_ordner_knopf.configure(state="disabled")
        self._startknopf(s.haupt(fuss, "Als ZIP speichern …", self.als_zip_speichern)).pack(side="right")
        self._startknopf(s.neben(fuss, "Nur exportieren", self.nur_exportieren, hoehe=44, breite=140)).pack(
            side="right", padx=(0, 10))
        return seite

    # --- Reaktionen auf Eingaben -----------------------------------------------

    def _spaeter(self, schluessel: str, aufgabe) -> None:
        """Beim Tippen nicht jeden Tastendruck einzeln verarbeiten."""
        if schluessel in self._nachlaeufe:
            self.fenster.after_cancel(self._nachlaeufe[schluessel])
        self._nachlaeufe[schluessel] = self.fenster.after(250, aufgabe)

    def _fotos_aktualisieren(self) -> None:
        if not self._gebaut("Entzerren"):
            return
        dateien = auftrag.bilder_finden(pfad(self.fotos.get()))
        self._bericht(self.fotos_info, auftrag.boegen_hinweis(dateien), "hinweis")
        self._schritt_stand("Entzerren", False)
        self.fotos_ansicht.zeige(dateien)

    def _boegen_aktualisieren(self) -> None:
        if self._gebaut("Erkennung prüfen"):
            self.pruef_ansicht.zeige(auftrag.bilder_finden(pfad(self.vorbereitet.get())))
            self._bericht(self.pruef_info, "Noch nicht geprüft.", "hinweis")
            self._schritt_stand("Erkennung prüfen", False)
        self._quelle_anzeigen()

    def _quelle_anzeigen(self) -> None:
        if not self._gebaut("Schrift erzeugen"):
            return
        dateien = auftrag.bilder_finden(pfad(self.vorbereitet.get()))
        self.quelle_info.configure(
            text=f"Aus {self.vorbereitet.get()} – {auftrag.boegen_hinweis(dateien)}")

    def _name_geaendert(self) -> None:
        # Der Zielordner folgt dem Namen, solange er nicht von Hand geändert wurde.
        if self.ziel.get() == f"Output/{self._alter_name}":
            self.ziel.set(f"Output/{self.name.get()}")
        self._alter_name = self.name.get()
        self._schritt_stand("Schrift erzeugen", False)

    def _strichbreite_geaendert(self) -> None:
        if not self._gebaut("Schrift erzeugen"):
            return
        aktiv = self.strichbreite_an.get()
        zustand = "normal" if aktiv else "disabled"
        self.strichbreite_regler.configure(state=zustand)
        self.strichbreite_feld.configure(state=zustand, text_color=TINTE if aktiv else GRAU)
        self.strichbreite_wert.configure(text=f"{self.strichbreite_anteil.get():.0%}" if aktiv else "")

    def _ohne_font_geaendert(self) -> None:
        if not self._gebaut("Schrift erzeugen"):
            return
        # „nur SVG“ und „SVG löschen“ zusammen würden nichts übrig lassen
        self.rmsvg_feld.configure(state="disabled" if self.ohne_font.get() else "normal")
        self.ohne_font_feld.configure(state="disabled" if self.rmsvg.get() else "normal")

    def _probe_groesse_geaendert(self) -> None:
        if not self._gebaut("Ergebnis"):
            return
        self.probe_groesse_text.configure(text=f"Schriftgröße {self.probe_groesse.get()}")
        self._spaeter("probe", self.probe_setzen)

    def _bericht(self, feld: ctk.CTkLabel, text: str, art: str) -> None:
        feld.configure(text=text, text_color=FARBEN[art])

    # --- Prozesse ---------------------------------------------------------------

    def _protokollieren(self, zeile: str, art: str | None = None) -> None:
        if self.protokoll is None:
            self._protokoll_puffer.append((zeile, art))
            return
        self.protokoll.configure(state="normal")
        self.protokoll.insert("end", zeile + "\n", art)
        self.protokoll.configure(state="disabled")
        self.protokoll.see("end")

    @property
    def beschaeftigt(self) -> bool:
        return self._prozess is not None

    def starten(self, befehl: list[str], titel: str, danach=None) -> None:
        """Skript im Hintergrund starten; ``danach(rueckgabewert)`` läuft im Tk-Thread."""
        self._protokollieren(f"$ {auftrag.anzeigen(befehl)}", "befehl")
        try:
            prozess = subprocess.Popen(
                befehl, cwd=auftrag.WURZEL, text=True, encoding="utf-8", errors="replace",
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        except OSError as fehler:
            self._protokollieren(f"Fehler: {fehler}", "fehler")
            self.protokoll_umschalten(True)
            return
        self._prozess = prozess
        self._danach = danach
        self._abgebrochen = False
        self.status.configure(text=f"{titel} …")
        self.abbruch.pack(side="right")
        self.fortschritt.pack(side="right", padx=10)
        self.fortschritt.start()
        for knopf in self._startknoepfe:
            knopf.configure(state="disabled")
        threading.Thread(target=self._mitlesen, args=(prozess,), daemon=True).start()

    def _mitlesen(self, prozess: subprocess.Popen) -> None:
        for zeile in prozess.stdout:
            self._zeilen.put(zeile.rstrip("\n"))
        self._zeilen.put((prozess.wait(),))

    def _ausgaben_abholen(self) -> None:
        try:
            while True:
                eintrag = self._zeilen.get_nowait()
                if isinstance(eintrag, tuple):
                    self._prozess_beendet(eintrag[0])
                elif auftrag.zeile_zeigen(eintrag):
                    self._protokollieren(eintrag, auftrag.zeilenart(eintrag))
        except queue.Empty:
            pass
        self._abholen = self.fenster.after(50, self._ausgaben_abholen)

    def _prozess_beendet(self, rueckgabe: int) -> None:
        self._prozess = None
        self.fortschritt.stop()
        self.fortschritt.pack_forget()
        self.abbruch.pack_forget()
        for knopf in self._startknoepfe:
            knopf.configure(state="normal")
        danach, self._danach = self._danach, None
        if self._abgebrochen:
            self.status.configure(text="Abgebrochen.")
            self._protokollieren("Abgebrochen.", "warnung")
            return
        self.status.configure(text="Fertig." if rueckgabe == 0 else f"Beendet mit Code {rueckgabe}.")
        if rueckgabe != 0:
            self.protokoll_umschalten(True)
        if danach:
            danach(rueckgabe)

    def abbrechen(self) -> None:
        if self._prozess:
            self._abgebrochen = True
            self._prozess.terminate()

    def beenden(self) -> None:
        if self.beschaeftigt:
            if not self._frage("Beenden?", "Es läuft noch ein Schritt. Er wird dann abgebrochen.", ja="Beenden"):
                return
            self._prozess.terminate()
        if self._waehler is not None:
            self._waehler.terminate()
        # auch die after-Aufträge von CustomTkinter, sonst meldet Tk beim Schließen Fehler
        for auftrag_id in self.fenster.tk.splitlist(self.fenster.tk.call("after", "info")):
            self.fenster.tk.call("after", "cancel", auftrag_id)
        self._temp.cleanup()
        self.fenster.destroy()

    # --- Start ------------------------------------------------------------------

    def vorlage_oeffnen(self) -> None:
        subprocess.Popen(["xdg-open", str(ZEICHENVORLAGE)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # --- Schritt 1 --------------------------------------------------------------

    def fotos_entzerren(self) -> None:
        fotos = auftrag.bilder_finden(pfad(self.fotos.get()))
        if not fotos:
            self._fehler("Scans entzerren", f"Keine Bilddateien ({auftrag.BILD_ARTEN}) in {self.fotos.get()}.")
            return
        ziel = pfad(self.vorbereitet.get())
        # Die Ergebnisse heißen immer <Name>.jpg, gleich welche Endung die Quelle hat.
        vorhanden = [f"{f.stem}.jpg" for f in fotos if (ziel / f"{f.stem}.jpg").exists()]
        if vorhanden and not self._frage(
                "Überschreiben?", f"In {self.vorbereitet.get()} liegen schon: {', '.join(vorhanden)}.",
                ja="Überschreiben"):
            return
        self.starten(auftrag.befehl_vorbereitung(pfad(self.fotos.get()), ziel), "Scans werden entzerrt",
                     self._fotos_fertig)

    def _fotos_fertig(self, rueckgabe: int) -> None:
        self._boegen_aktualisieren()
        if rueckgabe == 0:
            self._bericht(self.fotos_info, "Alle Scans sind entzerrt.", "ok")
            self._schritt_stand("Entzerren", True)
        else:
            self._bericht(self.fotos_info, "Nicht alle Scans konnten entzerrt werden, siehe Protokoll.", "fehler")

    # --- Schritt 2 --------------------------------------------------------------

    def erkennung_pruefen(self) -> None:
        scans = pfad(self.vorbereitet.get())
        if not auftrag.bilder_finden(scans):
            self._bericht(self.pruef_info, f"Keine Bilddateien ({auftrag.BILD_ARTEN}) in {self.vorbereitet.get()}.",
                          "fehler")
            return
        markiert = self.temp / "markiert"
        shutil.rmtree(markiert, ignore_errors=True)
        self.starten(auftrag.befehl_fehlersuche(scans, markiert), "Kästchen werden erkannt",
                     self._pruefung_fertig)

    def _pruefung_fertig(self, rueckgabe: int) -> None:
        bilder = auftrag.bilder_finden(self.temp / "markiert")
        self.pruef_ansicht.zeige(bilder)
        self._schritt_stand("Erkennung prüfen", bool(bilder))
        if rueckgabe == 0:
            self._bericht(self.pruef_info, "Alle Kästchen sicher erkannt.", "ok")
        elif bilder:
            self._bericht(self.pruef_info, "Unsichere Kästchen: Bitte Bild und Protokoll prüfen.", "warnung")
        else:
            self._bericht(self.pruef_info, "Die Prüfung ist fehlgeschlagen, siehe Protokoll.", "fehler")

    # --- Schritt 3 --------------------------------------------------------------

    def einstellungen(self) -> auftrag.ScanEinstellungen:
        """Eingaben einsammeln; ``ValueError`` mit verständlicher Meldung bei Unsinn."""
        fehler = auftrag.name_pruefen(self.name.get())
        if fehler:
            raise ValueError(fehler)
        if not self.ziel.get().strip():
            raise ValueError("Bitte einen Zielordner angeben.")
        strichbreite = None
        if self.strichbreite_an.get():
            try:
                strichbreite = auftrag.strichbreite_lesen(self.strichbreite.get())
            except ValueError:
                raise ValueError("Die Zielbreite muss eine Zahl größer 0 sein (oder leer bleiben).") from None
        return auftrag.ScanEinstellungen(
            scans=pfad(self.vorbereitet.get()),
            ziel=pfad(self.ziel.get()),
            name=self.name.get(),
            blur=int(self.blur.get()),
            stift=self.stift.get(),
            strichbreite_anteil=round(self.strichbreite_anteil.get(), 2) if self.strichbreite_an.get() else 0,
            strichbreite=strichbreite,
            ohne_font=self.ohne_font.get(),
            rmppm=self.rmppm.get(),
            rmjpg=self.rmjpg.get(),
            rmsvg=self.rmsvg.get(),
        )

    def _vorhandenes_bestaetigen(self, ziel: Path, name: str) -> bool:
        sfd = ziel / f"{name}-Regular.sfd"
        return not sfd.exists() or self._frage(
            "Überschreiben?", f"{sfd.name} gibt es in diesem Ordner schon.", ja="Überschreiben")

    def schrift_erzeugen(self) -> None:
        try:
            e = self.einstellungen()
        except ValueError as fehler:
            self._fehler("Schrift erzeugen", str(fehler))
            return
        if not auftrag.bilder_finden(e.scans):
            self._fehler("Schrift erzeugen",
                                 f"Keine Bilddateien ({auftrag.BILD_ARTEN}) in {self.vorbereitet.get()}.")
            return
        if not e.ohne_font and not self._vorhandenes_bestaetigen(e.ziel, e.name):
            return
        self.starten(auftrag.befehl_scan2svg(e), "Schrift wird erzeugt",
                     lambda rueckgabe: self._schrift_fertig(rueckgabe, e.ohne_font))

    def font_aus_svg(self) -> None:
        fehler = auftrag.name_pruefen(self.name.get())
        ziel = pfad(self.ziel.get())
        if not fehler and not (ziel.is_dir() and any(ziel.glob("*.svg"))):
            fehler = f"Keine *.svg-Dateien in {self.ziel.get()}."
        if fehler:
            self._fehler("Font aus SVG", fehler)
            return
        if self._vorhandenes_bestaetigen(ziel, self.name.get()):
            self.starten(auftrag.befehl_svg2font(ziel, self.name.get()),
                         "Font wird erzeugt", lambda rueckgabe: self._schrift_fertig(rueckgabe, False))

    def _schrift_fertig(self, rueckgabe: int, ohne_font: bool) -> None:
        if rueckgabe != 0:
            self._fehler("Schrift erzeugen", "Das hat nicht geklappt, Näheres steht im Protokoll.")
        elif ohne_font:
            self._protokollieren(f"SVG-Dateien liegen in {self.ziel.get()}.")
            self.status.configure(text=f"SVG-Dateien liegen in {self.ziel.get()}.")
        else:
            # wählt den neuen Font aus, der Seitenwechsel erzeugt dann die Schriftprobe
            self.sfd_auswahl.set(str(pfad(self.ziel.get()) / f"{self.name.get()}-Regular.sfd"))
            self.status.configure(text=f"{self.name.get()}-Regular.sfd ist erzeugt.")
            self._schritt_stand("Schrift erzeugen", True)

    # --- Schritt 6 --------------------------------------------------------------

    def export_formate_gewaehlt(self) -> list[str]:
        return [wert for wert, _, _, _ in EXPORT_FORMATE if self.export_an[wert].get()]

    def _export_aktualisieren(self) -> None:
        if not self._gebaut("Export"):
            return
        dateien = auftrag.sfd_dateien(pfad(self.ziel.get()))
        self._export_ort = None
        text = f"Noch keine Schriftdatei in {self.ziel.get()}."
        if dateien:
            text = f"{len(dateien)} Schriftdatei{'en' if len(dateien) > 1 else ''}: {', '.join(d.stem for d in dateien)}"
        self._bericht(self.export_info, text, "hinweis" if dateien else "warnung")
        self._bericht(self.export_bericht, "", "hinweis")

    def _export_starten(self, zip_ziel: Path | None) -> None:
        ordner = pfad(self.ziel.get())
        self._bericht(self.export_bericht, "Das kann einen Moment dauern …", "hinweis")
        self.starten(auftrag.befehl_export(ordner, self.export_formate_gewaehlt(), zip_ziel), "Export läuft",
                     lambda rueckgabe: self._export_fertig(rueckgabe, ordner, zip_ziel))

    def _export_pruefen(self) -> bool:
        if not auftrag.sfd_dateien(pfad(self.ziel.get())):
            self._fehler("Export", f"In {self.ziel.get()} gibt es noch keine Schriftdatei (*.sfd).")
            return False
        return True

    def nur_exportieren(self) -> None:
        if not self._export_pruefen():
            return
        if not self.export_formate_gewaehlt():
            self._fehler("Export", "Bitte mindestens ein Format auswählen.")
            return
        self._export_starten(None)

    def als_zip_speichern(self) -> None:
        if not self._export_pruefen():
            return
        ordner = pfad(self.ziel.get())
        dateien = auftrag.sfd_dateien(ordner)
        familie = dateien[0].stem.rpartition("-")[0] or dateien[0].stem
        gewaehlt = self._speichern_unter("ZIP speichern", ordner.parent / f"{familie}.zip")
        if gewaehlt:
            ziel = Path(gewaehlt)
            self._export_starten(ziel if ziel.suffix.lower() == ".zip" else ziel.with_name(ziel.name + ".zip"))

    def _export_fertig(self, rueckgabe: int, ordner: Path, zip_ziel: Path | None) -> None:
        if rueckgabe != 0:
            self._bericht(self.export_bericht, "Das hat nicht geklappt, siehe Protokoll.", "fehler")
            return
        if zip_ziel:
            groesse = zip_ziel.stat().st_size / 1024
            self._export_ort = zip_ziel.parent
            self._bericht(self.export_bericht, f"ZIP gespeichert ({groesse:.0f} KB): {zip_ziel}", "ok")
        else:
            self._export_ort = ordner / "export"
            self._bericht(self.export_bericht, f"Die Formate liegen in {ordner / 'export'}.", "ok")

    def export_ordner_oeffnen(self) -> None:
        ort = self._export_ort or pfad(self.ziel.get())
        if not ort.is_dir():
            self._fehler("Ordner öffnen", f"Den Ordner {ort} gibt es noch nicht.")
            return
        subprocess.Popen(["xdg-open", str(ort)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # --- Schritt 5 --------------------------------------------------------------

    def _schnitt_art_geaendert(self) -> None:
        ableiten = self.schnitt_art.get() == "ableiten"
        self.schnitt_staerke_regler.configure(state="normal" if ableiten else "disabled")
        self.schnitt_art_info.configure(text=(
            "Ein Ausgangspunkt für die weitere Arbeit in FontForge. Vorhandene Dateien werden ersetzt und als "
            "*.sfd.bak gesichert." if ableiten else
            "Für schon gestaltete Dateien neben der Regular-Datei; auch Regular wird passend gekennzeichnet."))

    def _schnitt_quelle_vorschlagen(self) -> None:
        if not self.schnitt_quelle.get().strip():
            vorschlag = pfad(self.ziel.get()) / f"{self.name.get()}-Regular.sfd"
            if vorschlag.is_file():
                self.schnitt_quelle.set(str(vorschlag))

    def _schnitt_quelle_waehlen(self) -> None:
        start = pfad(self.schnitt_quelle.get()).parent if self.schnitt_quelle.get().strip() else pfad(self.ziel.get())
        gewaehlt = self._waehlen("Überarbeitete Regular-Datei", start if start.is_dir() else auftrag.WURZEL,
                                 nur_sfd=True)
        if gewaehlt:
            self.schnitt_quelle.set(gewaehlt)

    def schnitte_erzeugen(self) -> None:
        regular = pfad(self.schnitt_quelle.get())
        stile = [stil for stil, _ in SCHNITTE if self.schnitt_an[stil].get()]
        stamm = auftrag.sfd_stamm(regular) if self.schnitt_quelle.get().strip() else None
        fehler = None
        if stamm is None:
            fehler = "Bitte die überarbeitete Regular-Datei (*.sfd) wählen."
        elif not stile:
            fehler = "Bitte mindestens einen Schnitt auswählen."
        elif regular.name.rpartition(".")[0].endswith(tuple(f"-{stil}" for stil in self.schnitt_an)):
            fehler = "Das ist schon ein abgeleiteter Schnitt. Bitte die Regular-Datei wählen."
        if fehler:
            self._fehler("Schriftschnitte", fehler)
            return
        nur_kennzeichen = self.schnitt_art.get() == "kennzeichen"
        dateien = {stil: regular.with_name(f"{stamm}-{stil}.sfd") for stil in stile}
        vorhanden = [d.name for d in dateien.values() if d.exists()]
        if nur_kennzeichen:
            fehlend = [d.name for d in dateien.values() if not d.exists()]
            if fehlend:
                self._fehler("Schriftschnitte", f"Diese Dateien fehlen noch: {', '.join(fehlend)}.\n\n"
                                     "Sie müssen neben der Regular-Datei liegen.")
                return
        elif vorhanden and not self._frage(
                "Überschreiben?", f"{', '.join(vorhanden)} gibt es schon. Nacharbeit darin wird ersetzt.\n"
                "Die alte Fassung bleibt als *.sfd.bak erhalten.", ja="Überschreiben"):
            return
        befehl = auftrag.befehl_schnitte(regular, stile, nur_kennzeichen, self.schnitt_staerke.get(),
                                         self.schnitt_neigung.get(), ueberschreiben=bool(vorhanden))
        self._bericht(self.schnitt_info, "Das kann eine Weile dauern …", "hinweis")
        self._schritt_stand("Schriftschnitte", False)
        self.starten(befehl, "Schriftschnitte werden erzeugt",
                     lambda rueckgabe: self._schnitte_fertig(rueckgabe, regular, dateien[stile[0]]))

    def _schnitte_fertig(self, rueckgabe: int, regular: Path, erster: Path) -> None:
        if rueckgabe != 0:
            self._bericht(self.schnitt_info, "Das hat nicht geklappt, siehe Protokoll.", "fehler")
            return
        self._bericht(self.schnitt_info, f"Fertig, die Dateien liegen neben {regular.name}.", "ok")
        # Das Ergebnis zeigt die neuen Schnitte, auch wenn die Regular-Datei woanders lag.
        try:
            self.ziel.set(str(regular.parent.relative_to(auftrag.WURZEL)))
        except ValueError:
            self.ziel.set(str(regular.parent))
        self.sfd_auswahl.set(str(erster))
        self._schritt_stand("Schriftschnitte", True)

    # --- Schritt 4 --------------------------------------------------------------

    def _sfd_gewaehlt(self, name: str) -> None:
        self.sfd_auswahl.set(str(pfad(self.ziel.get()) / name))
        self.probe_erzeugen()

    def ergebnis_aktualisieren(self) -> None:
        dateien = auftrag.sfd_dateien(pfad(self.ziel.get()))
        if self.sfd_auswahl.get() not in map(str, dateien):
            # Regular zuerst: Die Liste ist alphabetisch, dort stünde Bold vorn.
            regular = [d for d in dateien if d.stem.endswith("-Regular")]
            self.sfd_auswahl.set(str((regular or dateien)[0]) if dateien else "")
        vorhanden = bool(dateien)
        self.sfd_menue.configure(values=[d.name for d in dateien] or ["kein Font"],
                                 state="normal" if vorhanden else "disabled")
        self.sfd_menue.set(Path(self.sfd_auswahl.get()).name if vorhanden else "kein Font")
        self.fontforge_knopf.configure(state="normal" if vorhanden else "disabled")
        self.ergebnis_weiter.configure(state="normal" if vorhanden else "disabled")
        self.ordner_knopf.configure(state="normal" if vorhanden and shutil.which("xdg-open") else "disabled")
        if vorhanden:
            self.probe_erzeugen()
        else:
            self._otf = None
            self.probe_flaeche.delete("all")
            self._bericht(self.ergebnis_info, f"Noch kein Font in {self.ziel.get()}.", "hinweis")

    def probe_erzeugen(self) -> None:
        sfd = Path(self.sfd_auswahl.get())
        if not sfd.is_file() or self.beschaeftigt:
            return
        schluessel = (str(sfd), sfd.stat().st_mtime_ns)
        if schluessel in self._proben:
            self._probe_fertig(schluessel)
            return
        otf = self.temp / f"probe-{len(self._proben)}.otf"
        self._bericht(self.ergebnis_info, "Schriftprobe wird vorbereitet …", "hinweis")

        def danach(rueckgabe: int) -> None:
            if rueckgabe == 0 and otf.is_file():
                self._proben[schluessel] = otf
                self._probe_fertig(schluessel)
            else:
                self._otf = None
                self._bericht(self.ergebnis_info, "Die Schriftprobe konnte nicht erzeugt werden, siehe Protokoll.",
                              "fehler")

        self.starten(auftrag.befehl_schriftprobe(sfd, otf), "Schriftprobe wird vorbereitet", danach)

    def _probe_fertig(self, schluessel: tuple[str, int]) -> None:
        self._otf = self._proben[schluessel]
        self._bericht(self.ergebnis_info, f"Schriftprobe von {Path(schluessel[0]).name}. "
                                          "Überarbeiten Sie sie in FontForge. Danach geht es mit den Schnitten weiter, das ZIP gibt es unter „Export“.", "ok")
        self.probe_setzen()

    def probe_setzen(self) -> None:
        if self._otf is None or self.aktuell != "Ergebnis":
            return
        text = self.probe_text.get("1.0", "end-1c")
        bild = schriftprobe.setzen(self._otf, text, self.probe_groesse.get(),
                                   max(self.probe_flaeche.winfo_width(), 100))
        self._probe_foto = ImageTk.PhotoImage(bild)
        self.probe_flaeche.delete("all")
        self.probe_flaeche.create_image(0, 0, image=self._probe_foto, anchor="nw")
        self.probe_flaeche.configure(scrollregion=(0, 0, *bild.size))

    def in_fontforge_oeffnen(self) -> None:
        befehl = auftrag.befehl_fontforge(Path(self.sfd_auswahl.get()))
        if befehl is None:
            self._fontforge_fehlt()
            return
        self._protokollieren(f"$ {shlex.join(befehl)}", "befehl")
        prozess = subprocess.Popen(befehl, cwd=auftrag.WURZEL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        self.fenster.after(FONTFORGE_WARTEZEIT, lambda: self._fontforge_pruefen(prozess))

    def _fontforge_pruefen(self, prozess: subprocess.Popen) -> None:
        # Ein Programm mit Oberfläche läuft weiter, fontforge-nox beendet sich sofort.
        if prozess.poll() is not None:
            self._fontforge_fehlt()

    def _fontforge_fehlt(self) -> None:
        self._fehler(
            "In FontForge öffnen",
            "FontForge mit grafischer Oberfläche wurde nicht gefunden.\n\n"
            "Installieren lässt es sich z. B. mit\n"
            f"flatpak install flathub {auftrag.FONTFORGE_FLATPAK}\n"
            "oder\napt install fontforge")

    def ordner_oeffnen(self) -> None:
        subprocess.Popen(["xdg-open", str(Path(self.sfd_auswahl.get()).parent)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    fenster = ctk.CTk(className="Kritzelei")
    fenster.withdraw()  # erst zeigen, wenn alles aufgebaut ist
    Oberflaeche(fenster)
    fenster.deiconify()
    fenster.mainloop()
    return 0
