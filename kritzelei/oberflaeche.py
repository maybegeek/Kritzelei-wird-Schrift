"""Bedienoberfläche (Tk): führt in vier Schritten von den Fotos zur Schrift.

Die Arbeit erledigen die Kommandozeilen-Skripte, siehe ``auftrag.py``. Das
Protokoll im unteren Teil zeigt jeden Aufruf und alle Ausgaben.
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
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from . import auftrag, schriftprobe
from .auftrag import pfad
from .glyphen import BELEGUNG

SCHRIFTPROBE_TEXT = (
    "Franz jagt im komplett verwahrlosten Taxi quer durch Bayern.\n"
    "Zwölf Boxkämpfer jagen Viktor quer über den großen Sylter Deich.\n"
    "0123456789 – Kritzelei wird Schrift!"
)
LEGENDE = ("Blau: Soll-Raster der Vorlage · Grün: gefundener Rahmen (Orange: Lage geschätzt) · "
           "Rot: Ausschnitt, der zur Glyphe wird")
FARBE_OK = "#1b7a3d"
FARBE_WARNUNG = "#a85a00"
FARBE_FEHLER = "#b3261e"
RAND = 10
FONTFORGE_WARTEZEIT = 3000  # ms bis zur Kontrolle, ob FontForge noch läuft


class Bildansicht(ttk.Frame):
    """Bilderauswahl mit Anzeige: eingepasst oder in voller Größe (Doppelklick)."""

    def __init__(self, eltern, leertext: str):
        super().__init__(eltern)
        self.leertext = leertext
        self.dateien: list[Path] = []
        self.auswahl = tk.StringVar()
        self.einpassen = True
        self._bild: Image.Image | None = None
        self._foto = None
        self._nachlauf = None
        self._versatz = (0, 0, 1.0)

        kopf = ttk.Frame(self)
        kopf.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        self._knoepfe = ttk.Frame(kopf)
        self._knoepfe.pack(side="left")
        self._zoom = ttk.Button(kopf, text="Volle Größe", command=self.umschalten)
        self._zoom.pack(side="right")
        ttk.Label(kopf, text="Doppelklick vergrößert, Ziehen verschiebt",
                  foreground="#666666").pack(side="right", padx=8)

        self.flaeche = tk.Canvas(self, background="#d9d9d9", highlightthickness=0)
        leiste_y = ttk.Scrollbar(self, orient="vertical", command=self.flaeche.yview)
        leiste_x = ttk.Scrollbar(self, orient="horizontal", command=self.flaeche.xview)
        self.flaeche.configure(xscrollcommand=leiste_x.set, yscrollcommand=leiste_y.set)
        self.flaeche.grid(row=1, column=0, sticky="nsew")
        leiste_y.grid(row=1, column=1, sticky="ns")
        leiste_x.grid(row=2, column=0, sticky="ew")
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.flaeche.bind("<Configure>", self._groesse_geaendert)
        self.flaeche.bind("<ButtonPress-1>", lambda e: self.flaeche.scan_mark(e.x, e.y))
        self.flaeche.bind("<B1-Motion>", lambda e: self.flaeche.scan_dragto(e.x, e.y, gain=1))
        self.flaeche.bind("<Double-Button-1>", self.umschalten)

    def zeige(self, dateien: list[Path]) -> None:
        """Bilder neu einlesen; dasselbe Blatt bleibt ausgewählt, wenn es noch da ist."""
        self.dateien = dateien
        for knopf in self._knoepfe.winfo_children():
            knopf.destroy()
        namen = [d.name for d in dateien]
        for name in namen:
            ttk.Radiobutton(self._knoepfe, text=name, value=name, variable=self.auswahl,
                            style="Toolbutton", command=self._laden).pack(side="left", padx=(0, 2))
        if self.auswahl.get() not in namen:
            self.auswahl.set(namen[0] if namen else "")
        self._laden()

    def _laden(self) -> None:
        name = self.auswahl.get()
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
            self.flaeche.create_text(breite // 2, hoehe // 2, text=self.leertext, fill="#555555",
                                     width=max(breite - 40, 100), justify="center")
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


class Oberflaeche:
    def __init__(self, fenster: tk.Tk):
        self.fenster = fenster
        self._temp = tempfile.TemporaryDirectory(prefix="kritzelei-")
        self.temp = Path(self._temp.name)
        self._prozess: subprocess.Popen | None = None
        self._zeilen: queue.Queue = queue.Queue()
        self._danach = None
        self._abgebrochen = False
        self._startknoepfe: list[ttk.Button] = []
        self._proben: dict[tuple[str, int], Path] = {}
        self._otf: Path | None = None
        self._probe_foto = None
        self._nachlaeufe: dict[str, str] = {}

        fenster.title("Kritzelei wird Schrift")
        fenster.geometry("1100x860")
        fenster.minsize(880, 680)
        fenster.protocol("WM_DELETE_WINDOW", self.beenden)
        self._stil()

        # Einstellungen; der Ordner der vorbereiteten Bögen gilt für alle Schritte
        self.fotos = tk.StringVar(value="Kritzelei-Bilder-Original")
        self.vorbereitet = tk.StringVar(value="Kritzelei-Bilder-Vorbereitung")
        self.version = tk.StringVar(value=str(max(BELEGUNG)))
        self.erkennung = tk.StringVar(value=auftrag.AUTOMATISCH)
        self.schwellwert = tk.IntVar(value=100)
        self.name = tk.StringVar(value="Kritzelei-01")
        self.ziel = tk.StringVar(value="Output/Kritzelei-01")
        self.stift = tk.StringVar(value="standard")
        self.blur = tk.StringVar(value="3")
        self.breite_an = tk.BooleanVar(value=True)
        self.breite_anteil = tk.DoubleVar(value=auftrag.ScanEinstellungen.breite_anteil)
        self.strichbreite = tk.StringVar()
        self.skel = tk.BooleanVar(value=False)
        self.ohne_font = tk.BooleanVar(value=False)
        self.rmppm = tk.BooleanVar(value=True)
        self.rmjpg = tk.BooleanVar(value=False)
        self.rmsvg = tk.BooleanVar(value=False)
        self.sfd_auswahl = tk.StringVar()
        self.probe_groesse = tk.IntVar(value=48)
        self._alter_name = self.name.get()

        teiler = ttk.PanedWindow(fenster, orient="vertical")
        teiler.pack(fill="both", expand=True, padx=RAND, pady=RAND)
        self.reiter = ttk.Notebook(teiler)
        teiler.add(self.reiter, weight=5)
        teiler.add(self._protokoll_bauen(teiler), weight=1)

        self.schritt1 = self._schritt_fotos()
        self.schritt2 = self._schritt_pruefen()
        self.schritt3 = self._schritt_erzeugen()
        self.schritt4 = self._schritt_ergebnis()
        self.reiter.add(self.schritt1, text="1  Fotos entzerren")
        self.reiter.add(self.schritt2, text="2  Erkennung prüfen")
        self.reiter.add(self.schritt3, text="3  Schrift erzeugen")
        self.reiter.add(self.schritt4, text="4  Ergebnis")
        self.reiter.bind("<<NotebookTabChanged>>", self._reiter_gewechselt)

        self.fotos.trace_add("write", lambda *_: self._spaeter("fotos", self._fotos_aktualisieren))
        self.vorbereitet.trace_add("write", lambda *_: self._spaeter("boegen", self._boegen_aktualisieren))
        self.name.trace_add("write", lambda *_: self._name_geaendert())
        for variable in (self.version, self.erkennung):
            variable.trace_add("write", lambda *_: self._erkennung_geaendert())
        self.breite_an.trace_add("write", lambda *_: self._breite_geaendert())
        self.breite_anteil.trace_add("write", lambda *_: self._breite_geaendert())
        self.ohne_font.trace_add("write", lambda *_: self._ohne_font_geaendert())
        self.rmsvg.trace_add("write", lambda *_: self._ohne_font_geaendert())
        self.probe_groesse.trace_add("write", lambda *_: self._spaeter("probe", self.probe_setzen))

        self._fotos_aktualisieren()
        self._boegen_aktualisieren()
        self._erkennung_geaendert()
        self._breite_geaendert()
        self._ohne_font_geaendert()
        self.fenster.after(50, self._ausgaben_abholen)

    # --- Aufbau ----------------------------------------------------------------

    def _stil(self) -> None:
        stil = ttk.Style(self.fenster)
        if "clam" in stil.theme_names():
            stil.theme_use("clam")
        stil.configure("Start.TButton", font="TkDefaultFont 10 bold", padding=(14, 6))
        stil.configure("Hinweis.TLabel", foreground="#555555")
        stil.configure("Ok.TLabel", foreground=FARBE_OK)
        stil.configure("Warnung.TLabel", foreground=FARBE_WARNUNG)
        stil.configure("Fehler.TLabel", foreground=FARBE_FEHLER)
        stil.configure("TLabelframe", padding=RAND)
        stil.configure("TNotebook.Tab", padding=(12, 5))

    def _protokoll_bauen(self, eltern) -> ttk.Frame:
        rahmen = ttk.Frame(eltern)
        kopf = ttk.Frame(rahmen)
        kopf.pack(fill="x", pady=(6, 4))
        ttk.Label(kopf, text="Protokoll").pack(side="left")
        self.status = ttk.Label(kopf, text="Bereit.", style="Hinweis.TLabel")
        self.status.pack(side="left", padx=10)
        self.abbruch = ttk.Button(kopf, text="Abbrechen", command=self.abbrechen, state="disabled")
        self.abbruch.pack(side="right")
        self.fortschritt = ttk.Progressbar(kopf, mode="indeterminate", length=160)

        unten = ttk.Frame(rahmen)
        unten.pack(fill="both", expand=True)
        self.protokoll = tk.Text(unten, height=9, wrap="word", state="disabled", font="TkFixedFont",
                                 background="#fbfbfb", relief="solid", borderwidth=1)
        leiste = ttk.Scrollbar(unten, orient="vertical", command=self.protokoll.yview)
        self.protokoll.configure(yscrollcommand=leiste.set)
        self.protokoll.pack(side="left", fill="both", expand=True)
        leiste.pack(side="right", fill="y")
        self.protokoll.tag_configure("befehl", foreground="#3b5bdb")
        self.protokoll.tag_configure("warnung", foreground=FARBE_WARNUNG)
        self.protokoll.tag_configure("fehler", foreground=FARBE_FEHLER)
        return rahmen

    def _ordnerzeile(self, eltern, zeile: int, text: str, variable: tk.StringVar) -> None:
        ttk.Label(eltern, text=text).grid(row=zeile, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(eltern, textvariable=variable).grid(row=zeile, column=1, sticky="ew", pady=3)
        ttk.Button(eltern, text="Wählen …", command=lambda: self._ordner_waehlen(variable, text)).grid(
            row=zeile, column=2, padx=(6, 0), pady=3)
        eltern.columnconfigure(1, weight=1)

    def _ordner_waehlen(self, variable: tk.StringVar, titel: str) -> None:
        start = pfad(variable.get())
        gewaehlt = filedialog.askdirectory(parent=self.fenster, title=titel,
                                           initialdir=str(start if start.is_dir() else auftrag.WURZEL))
        if gewaehlt:
            try:
                variable.set(str(Path(gewaehlt).relative_to(auftrag.WURZEL)))
            except ValueError:
                variable.set(gewaehlt)

    def _startknopf(self, eltern, text: str, befehl) -> ttk.Button:
        knopf = ttk.Button(eltern, text=text, command=befehl, style="Start.TButton")
        self._startknoepfe.append(knopf)
        return knopf

    def _schritt_fotos(self) -> ttk.Frame:
        seite = ttk.Frame(self.reiter, padding=RAND)
        ttk.Label(seite, style="Hinweis.TLabel",
                  text="Die Fotos oder Scans der ausgefüllten Bögen werden anhand der vier Randmarken "
                       "entzerrt und zugeschnitten.").pack(anchor="w", pady=(0, 6))
        form = ttk.Frame(seite)
        form.pack(fill="x")
        self._ordnerzeile(form, 0, "Fotos (*.jpg)", self.fotos)
        self._ordnerzeile(form, 1, "Vorbereitete Bögen", self.vorbereitet)
        zeile = ttk.Frame(seite)
        zeile.pack(fill="x", pady=8)
        self._startknopf(zeile, "Fotos entzerren", self.fotos_entzerren).pack(side="left")
        self.fotos_info = ttk.Label(zeile, style="Hinweis.TLabel")
        self.fotos_info.pack(side="left", padx=10)
        self.fotos_ansicht = Bildansicht(seite, "Hier erscheinen die Fotos aus dem gewählten Ordner.")
        self.fotos_ansicht.pack(fill="both", expand=True)
        return seite

    def _schritt_pruefen(self) -> ttk.Frame:
        seite = ttk.Frame(self.reiter, padding=RAND)
        form = ttk.Frame(seite)
        form.pack(fill="x")
        self._ordnerzeile(form, 0, "Vorbereitete Bögen", self.vorbereitet)

        wahl = ttk.Frame(seite)
        wahl.pack(fill="x", pady=4)
        ttk.Label(wahl, text="Vorlage").pack(side="left")
        ttk.Combobox(wahl, textvariable=self.version, state="readonly", width=4,
                     values=[str(v) for v in sorted(BELEGUNG)]).pack(side="left", padx=(6, 16))
        ttk.Label(wahl, text="Kästchenerkennung").pack(side="left")
        ttk.Combobox(wahl, textvariable=self.erkennung, state="readonly", width=12,
                     values=auftrag.ERKENNUNG_AUSWAHL).pack(side="left", padx=(6, 16))
        self.schwellwert_text = ttk.Label(wahl, text="Schwellwert")
        self.schwellwert_text.pack(side="left")
        self.schwellwert_feld = ttk.Spinbox(wahl, textvariable=self.schwellwert, from_=0, to=255, width=5)
        self.schwellwert_feld.pack(side="left", padx=6)

        zeile = ttk.Frame(seite)
        zeile.pack(fill="x", pady=8)
        self._startknopf(zeile, "Erkennung prüfen", self.erkennung_pruefen).pack(side="left")
        self.pruef_info = ttk.Label(zeile, style="Hinweis.TLabel", text="Noch nicht geprüft.")
        self.pruef_info.pack(side="left", padx=10)
        ttk.Label(seite, text=LEGENDE, style="Hinweis.TLabel").pack(anchor="w", pady=(0, 6))
        self.pruef_ansicht = Bildansicht(seite, "Hier erscheinen die Bögen mit den erkannten Kästchen.")
        self.pruef_ansicht.pack(fill="both", expand=True)
        return seite

    def _schritt_erzeugen(self) -> ttk.Frame:
        seite = ttk.Frame(self.reiter, padding=RAND)
        seite.columnconfigure((0, 1), weight=1, uniform="spalte")

        schrift = ttk.LabelFrame(seite, text="Schrift")
        schrift.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, RAND))
        ttk.Label(schrift, text="Name").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(schrift, textvariable=self.name).grid(row=0, column=1, sticky="ew", pady=3)
        self._ordnerzeile(schrift, 1, "Zielordner", self.ziel)
        self.quelle_info = ttk.Label(schrift, style="Hinweis.TLabel", wraplength=820)
        self.quelle_info.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))

        stift = ttk.LabelFrame(seite, text="Stift")
        stift.grid(row=1, column=0, sticky="nsew", padx=(0, RAND // 2))
        for wert, text in auftrag.STIFT_AUSWAHL.items():
            ttk.Radiobutton(stift, text=text, value=wert, variable=self.stift).pack(anchor="w", pady=2)
        blur = ttk.Frame(stift)
        blur.pack(anchor="w", pady=(8, 0))
        ttk.Label(blur, text="Weichzeichner").pack(side="left")
        ttk.Combobox(blur, textvariable=self.blur, state="readonly", width=3,
                     values=["0", "1", "3", "5", "7", "9"]).pack(side="left", padx=6)
        ttk.Label(blur, text="(0 = aus)", style="Hinweis.TLabel").pack(side="left")

        breite = ttk.LabelFrame(seite, text="Strichbreite")
        breite.grid(row=1, column=1, sticky="nsew", padx=(RAND // 2, 0))
        breite.columnconfigure(1, weight=1)
        ttk.Checkbutton(breite, text="Strichbreiten aller Zeichen einander annähern",
                        variable=self.breite_an).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(breite, text="Stärke").grid(row=1, column=0, sticky="w", pady=6)
        self.breite_regler = ttk.Scale(breite, from_=0.1, to=1.0, variable=self.breite_anteil)
        self.breite_regler.grid(row=1, column=1, sticky="ew", padx=6)
        self.breite_wert = ttk.Label(breite, width=6)
        self.breite_wert.grid(row=1, column=2)
        ttk.Label(breite, text="Zielbreite").grid(row=2, column=0, sticky="w")
        self.strichbreite_feld = ttk.Entry(breite, textvariable=self.strichbreite, width=8)
        self.strichbreite_feld.grid(row=2, column=1, sticky="w", padx=6)
        ttk.Label(breite, text="Font-Einheiten; leer = Median aller Zeichen",
                  style="Hinweis.TLabel").grid(row=3, column=0, columnspan=3, sticky="w", pady=(2, 0))

        extras = ttk.LabelFrame(seite, text="Zusätze")
        extras.grid(row=2, column=0, sticky="nsew", padx=(0, RAND // 2), pady=(RAND, 0))
        ttk.Checkbutton(extras, text="Zweiter Font mit einheitlicher Strichstärke (Unterordner SKEL)",
                        variable=self.skel).pack(anchor="w", pady=2)
        self.ohne_font_feld = ttk.Checkbutton(extras, text="Nur SVG-Dateien erzeugen, keinen Font",
                                              variable=self.ohne_font)
        self.ohne_font_feld.pack(anchor="w", pady=2)

        aufraeumen = ttk.LabelFrame(seite, text="Zwischendateien am Ende löschen")
        aufraeumen.grid(row=2, column=1, sticky="nsew", padx=(RAND // 2, 0), pady=(RAND, 0))
        ttk.Checkbutton(aufraeumen, text="PPM", variable=self.rmppm).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(aufraeumen, text="JPG", variable=self.rmjpg).pack(side="left", padx=(0, 12))
        self.rmsvg_feld = ttk.Checkbutton(aufraeumen, text="SVG", variable=self.rmsvg)
        self.rmsvg_feld.pack(side="left")

        zeile = ttk.Frame(seite)
        zeile.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        self._startknopf(zeile, "Schrift erzeugen", self.schrift_erzeugen).pack(side="left")
        svg = ttk.Button(zeile, text="Nur Font aus vorhandenen SVG-Dateien im Zielordner",
                         command=self.font_aus_svg)
        svg.pack(side="left", padx=10)
        self._startknoepfe.append(svg)
        return seite

    def _schritt_ergebnis(self) -> ttk.Frame:
        seite = ttk.Frame(self.reiter, padding=RAND)
        kopf = ttk.Frame(seite)
        kopf.pack(fill="x")
        ttk.Label(kopf, text="Font").pack(side="left")
        self.sfd_feld = ttk.Combobox(kopf, textvariable=self.sfd_auswahl, state="readonly")
        self.sfd_feld.pack(side="left", fill="x", expand=True, padx=6)
        self.sfd_feld.bind("<<ComboboxSelected>>", lambda _: self.probe_erzeugen())
        self.fontforge_knopf = ttk.Button(kopf, text="In FontForge öffnen", command=self.in_fontforge_oeffnen)
        self.fontforge_knopf.pack(side="left", padx=(0, 6))
        self.ordner_knopf = ttk.Button(kopf, text="Ordner öffnen", command=self.ordner_oeffnen)
        self.ordner_knopf.pack(side="left")

        self.ergebnis_info = ttk.Label(seite, style="Hinweis.TLabel",
                                       text="Hier erscheint die Schrift, sobald sie erzeugt ist.")
        self.ergebnis_info.pack(anchor="w", pady=6)

        probe = ttk.Frame(seite)
        probe.pack(fill="x", pady=(0, 6))
        self.probe_text = tk.Text(probe, height=3, wrap="word", relief="solid", borderwidth=1)
        self.probe_text.insert("1.0", SCHRIFTPROBE_TEXT)
        self.probe_text.pack(side="left", fill="x", expand=True)
        self.probe_text.bind("<KeyRelease>", lambda _: self._spaeter("probe", self.probe_setzen))
        groesse = ttk.Frame(probe)
        groesse.pack(side="left", padx=(10, 0))
        ttk.Label(groesse, text="Schriftgröße").pack()
        ttk.Spinbox(groesse, textvariable=self.probe_groesse, from_=12, to=200, increment=4, width=5).pack()

        flaeche = ttk.Frame(seite)
        flaeche.pack(fill="both", expand=True)
        self.probe_flaeche = tk.Canvas(flaeche, background="white", highlightthickness=1,
                                       highlightbackground="#bbbbbb")
        leiste = ttk.Scrollbar(flaeche, orient="vertical", command=self.probe_flaeche.yview)
        self.probe_flaeche.configure(yscrollcommand=leiste.set)
        self.probe_flaeche.pack(side="left", fill="both", expand=True)
        leiste.pack(side="right", fill="y")
        self.probe_flaeche.bind("<Configure>", lambda _: self._spaeter("probe", self.probe_setzen))
        return seite

    # --- Reaktionen auf Eingaben -----------------------------------------------

    def _spaeter(self, schluessel: str, aufgabe) -> None:
        """Beim Tippen nicht jeden Tastendruck einzeln verarbeiten."""
        if schluessel in self._nachlaeufe:
            self.fenster.after_cancel(self._nachlaeufe[schluessel])
        self._nachlaeufe[schluessel] = self.fenster.after(250, aufgabe)

    def _fotos_aktualisieren(self) -> None:
        dateien = auftrag.bilder_finden(pfad(self.fotos.get()))
        self._bericht(self.fotos_info, auftrag.boegen_hinweis(dateien), "Hinweis.TLabel")
        self.fotos_ansicht.zeige(dateien)

    def _boegen_aktualisieren(self) -> None:
        dateien = auftrag.bilder_finden(pfad(self.vorbereitet.get()))
        self.pruef_ansicht.zeige(dateien)
        self._bericht(self.pruef_info, "Noch nicht geprüft.", "Hinweis.TLabel")
        self._quelle_anzeigen()

    def _quelle_anzeigen(self) -> None:
        dateien = auftrag.bilder_finden(pfad(self.vorbereitet.get()))
        self.quelle_info.configure(
            text=f"Aus {self.vorbereitet.get()} – {auftrag.boegen_hinweis(dateien)} "
                 f"Vorlage {self.version.get()}, Erkennung {self.erkennung.get()} (siehe Schritt 2).")

    def _name_geaendert(self) -> None:
        # Der Zielordner folgt dem Namen, solange er nicht von Hand geändert wurde.
        if self.ziel.get() == f"Output/{self._alter_name}":
            self.ziel.set(f"Output/{self.name.get()}")
        self._alter_name = self.name.get()

    def _erkennung_geaendert(self) -> None:
        aktiv = auftrag.schwellwert_aktiv(int(self.version.get()), self.erkennung.get())
        self.schwellwert_feld.state(["!disabled"] if aktiv else ["disabled"])
        self.schwellwert_text.state(["!disabled"] if aktiv else ["disabled"])
        self._bericht(self.pruef_info, "Noch nicht geprüft.", "Hinweis.TLabel")
        self._quelle_anzeigen()

    def _breite_geaendert(self) -> None:
        aktiv = self.breite_an.get()
        for feld in (self.breite_regler, self.strichbreite_feld):
            feld.state(["!disabled"] if aktiv else ["disabled"])
        self.breite_wert.configure(text=f"{self.breite_anteil.get():.0%}" if aktiv else "")

    def _ohne_font_geaendert(self) -> None:
        # „nur SVG“ und „SVG löschen“ zusammen würden nichts übrig lassen
        self.rmsvg_feld.state(["disabled"] if self.ohne_font.get() else ["!disabled"])
        self.ohne_font_feld.state(["disabled"] if self.rmsvg.get() else ["!disabled"])

    def _reiter_gewechselt(self, _ereignis) -> None:
        if self.reiter.select() == str(self.schritt4):
            self.ergebnis_aktualisieren()

    def _bericht(self, feld: ttk.Label, text: str, stil: str) -> None:
        feld.configure(text=text, style=stil)

    # --- Prozesse ---------------------------------------------------------------

    def _protokollieren(self, zeile: str, art: str | None = None) -> None:
        self.protokoll.configure(state="normal")
        self.protokoll.insert("end", zeile + "\n", art or ())
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
            return
        self._prozess = prozess
        self._danach = danach
        self._abgebrochen = False
        self.status.configure(text=f"{titel} …")
        self.abbruch.configure(state="normal")
        self.fortschritt.pack(side="right", padx=8)
        self.fortschritt.start(12)
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
        self.fenster.after(50, self._ausgaben_abholen)

    def _prozess_beendet(self, rueckgabe: int) -> None:
        self._prozess = None
        self.fortschritt.stop()
        self.fortschritt.pack_forget()
        self.abbruch.configure(state="disabled")
        for knopf in self._startknoepfe:
            knopf.configure(state="normal")
        danach, self._danach = self._danach, None
        if self._abgebrochen:
            self.status.configure(text="Abgebrochen.")
            self._protokollieren("Abgebrochen.", "warnung")
            return
        self.status.configure(text="Fertig." if rueckgabe == 0 else f"Beendet mit Code {rueckgabe}.")
        if danach:
            danach(rueckgabe)

    def abbrechen(self) -> None:
        if self._prozess:
            self._abgebrochen = True
            self._prozess.terminate()

    def beenden(self) -> None:
        if self.beschaeftigt:
            if not messagebox.askyesno("Beenden", "Es läuft noch ein Schritt. Abbrechen und beenden?",
                                       parent=self.fenster):
                return
            self._prozess.terminate()
        self._temp.cleanup()
        self.fenster.destroy()

    # --- Schritt 1 --------------------------------------------------------------

    def fotos_entzerren(self) -> None:
        fotos = auftrag.bilder_finden(pfad(self.fotos.get()))
        if not fotos:
            messagebox.showerror("Fotos entzerren", f"Keine *.jpg-Dateien in {self.fotos.get()}.",
                                 parent=self.fenster)
            return
        ziel = pfad(self.vorbereitet.get())
        vorhanden = [f.name for f in fotos if (ziel / f.name).exists()]
        if vorhanden and not messagebox.askyesno(
                "Überschreiben?",
                f"In {self.vorbereitet.get()} liegen schon: {', '.join(vorhanden)}.\nÜberschreiben?",
                parent=self.fenster):
            return
        self.starten(auftrag.befehl_vorbereitung(pfad(self.fotos.get()), ziel), "Fotos werden entzerrt",
                     self._fotos_fertig)

    def _fotos_fertig(self, rueckgabe: int) -> None:
        self._boegen_aktualisieren()
        if rueckgabe == 0:
            self.reiter.select(self.schritt2)
            self.erkennung_pruefen()
        else:
            self._bericht(self.fotos_info, "Nicht alle Fotos konnten entzerrt werden, siehe Protokoll.",
                          "Fehler.TLabel")

    # --- Schritt 2 --------------------------------------------------------------

    def erkennung_pruefen(self) -> None:
        scans = pfad(self.vorbereitet.get())
        if not auftrag.bilder_finden(scans):
            self._bericht(self.pruef_info, f"Keine *.jpg-Dateien in {self.vorbereitet.get()}.", "Fehler.TLabel")
            return
        markiert = self.temp / "markiert"
        shutil.rmtree(markiert, ignore_errors=True)
        befehl = auftrag.befehl_fehlersuche(scans, int(self.version.get()), self.erkennung.get(),
                                            self.schwellwert.get(), markiert)
        self.starten(befehl, "Kästchen werden erkannt", self._pruefung_fertig)

    def _pruefung_fertig(self, rueckgabe: int) -> None:
        bilder = auftrag.bilder_finden(self.temp / "markiert")
        self.pruef_ansicht.zeige(bilder)
        if rueckgabe == 0:
            self._bericht(self.pruef_info, "Alle Kästchen sicher erkannt – weiter mit Schritt 3.", "Ok.TLabel")
        elif bilder:
            self._bericht(self.pruef_info, "Unsichere Kästchen: Bitte Bild und Protokoll prüfen.",
                          "Warnung.TLabel")
        else:
            self._bericht(self.pruef_info, "Die Prüfung ist fehlgeschlagen, siehe Protokoll.", "Fehler.TLabel")

    # --- Schritt 3 --------------------------------------------------------------

    def einstellungen(self) -> auftrag.ScanEinstellungen:
        """Eingaben einsammeln; ``ValueError`` mit verständlicher Meldung bei Unsinn."""
        fehler = auftrag.name_pruefen(self.name.get())
        if fehler:
            raise ValueError(fehler)
        if not self.ziel.get().strip():
            raise ValueError("Bitte einen Zielordner angeben.")
        strichbreite = None
        if self.breite_an.get():
            try:
                strichbreite = auftrag.strichbreite_lesen(self.strichbreite.get())
            except ValueError:
                raise ValueError("Die Zielbreite muss eine Zahl größer 0 sein (oder leer bleiben).") from None
        return auftrag.ScanEinstellungen(
            scans=pfad(self.vorbereitet.get()),
            ziel=pfad(self.ziel.get()),
            name=self.name.get(),
            version=int(self.version.get()),
            erkennung=self.erkennung.get(),
            schwellwert=self.schwellwert.get(),
            blur=int(self.blur.get()),
            stift=self.stift.get(),
            breite_anteil=round(self.breite_anteil.get(), 2) if self.breite_an.get() else 0,
            strichbreite=strichbreite,
            skel=self.skel.get(),
            ohne_font=self.ohne_font.get(),
            rmppm=self.rmppm.get(),
            rmjpg=self.rmjpg.get(),
            rmsvg=self.rmsvg.get(),
        )

    def _vorhandenes_bestaetigen(self, ziel: Path, name: str) -> bool:
        sfd = ziel / f"{name}-Regular.sfd"
        return not sfd.exists() or messagebox.askyesno(
            "Überschreiben?", f"{sfd.name} gibt es in diesem Ordner schon.\nÜberschreiben?", parent=self.fenster)

    def schrift_erzeugen(self) -> None:
        try:
            e = self.einstellungen()
        except ValueError as fehler:
            messagebox.showerror("Schrift erzeugen", str(fehler), parent=self.fenster)
            return
        if not auftrag.bilder_finden(e.scans):
            messagebox.showerror("Schrift erzeugen", f"Keine *.jpg-Dateien in {self.vorbereitet.get()}.",
                                 parent=self.fenster)
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
            messagebox.showerror("Font aus SVG", fehler, parent=self.fenster)
            return
        if self._vorhandenes_bestaetigen(ziel, self.name.get()):
            self.starten(auftrag.befehl_svg2font(ziel, self.name.get(), int(self.version.get())),
                         "Font wird erzeugt", lambda rueckgabe: self._schrift_fertig(rueckgabe, False))

    def _schrift_fertig(self, rueckgabe: int, ohne_font: bool) -> None:
        if rueckgabe != 0:
            messagebox.showerror("Schrift erzeugen", "Das hat nicht geklappt, Näheres steht im Protokoll.",
                                 parent=self.fenster)
        elif ohne_font:
            self._protokollieren(f"SVG-Dateien liegen in {self.ziel.get()}.")
        else:
            # wählt den neuen Font aus, der Reiterwechsel erzeugt dann die Schriftprobe
            self.sfd_auswahl.set(str(pfad(self.ziel.get()) / f"{self.name.get()}-Regular.sfd"))
            if self.reiter.select() == str(self.schritt4):
                self.ergebnis_aktualisieren()
            else:
                self.reiter.select(self.schritt4)

    # --- Schritt 4 --------------------------------------------------------------

    def ergebnis_aktualisieren(self) -> None:
        dateien = auftrag.sfd_dateien(pfad(self.ziel.get()))
        self.sfd_feld.configure(values=[str(d) for d in dateien])
        if self.sfd_auswahl.get() not in map(str, dateien):
            self.sfd_auswahl.set(str(dateien[0]) if dateien else "")
        vorhanden = bool(dateien)
        self.fontforge_knopf.configure(state="normal" if vorhanden else "disabled")
        self.ordner_knopf.configure(state="normal" if vorhanden and shutil.which("xdg-open") else "disabled")
        if vorhanden:
            self.probe_erzeugen()
        else:
            self._otf = None
            self.probe_flaeche.delete("all")
            self._bericht(self.ergebnis_info, f"Noch kein Font in {self.ziel.get()}.", "Hinweis.TLabel")

    def probe_erzeugen(self) -> None:
        sfd = Path(self.sfd_auswahl.get())
        if not sfd.is_file() or self.beschaeftigt:
            return
        schluessel = (str(sfd), sfd.stat().st_mtime_ns)
        if schluessel in self._proben:
            self._probe_fertig(schluessel)
            return
        otf = self.temp / f"probe-{len(self._proben)}.otf"
        self._bericht(self.ergebnis_info, "Schriftprobe wird vorbereitet …", "Hinweis.TLabel")

        def danach(rueckgabe: int) -> None:
            if rueckgabe == 0 and otf.is_file():
                self._proben[schluessel] = otf
                self._probe_fertig(schluessel)
            else:
                self._otf = None
                self._bericht(self.ergebnis_info, "Die Schriftprobe konnte nicht erzeugt werden, siehe Protokoll.",
                              "Fehler.TLabel")

        self.starten(auftrag.befehl_schriftprobe(sfd, otf), "Schriftprobe wird vorbereitet", danach)

    def _probe_fertig(self, schluessel: tuple[str, int]) -> None:
        self._otf = self._proben[schluessel]
        self._bericht(self.ergebnis_info, f"Schriftprobe von {Path(schluessel[0]).name}. "
                                          "Den Feinschliff und den Export übernimmt FontForge.", "Ok.TLabel")
        self.probe_setzen()

    def probe_setzen(self) -> None:
        if self._otf is None:
            return
        try:
            groesse = self.probe_groesse.get()
        except tk.TclError:  # Feld gerade leer getippt
            return
        text = self.probe_text.get("1.0", "end-1c")
        bild = schriftprobe.setzen(self._otf, text, max(6, groesse), max(self.probe_flaeche.winfo_width(), 100))
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
        messagebox.showerror(
            "In FontForge öffnen",
            "FontForge mit grafischer Oberfläche wurde nicht gefunden.\n\n"
            "Installieren lässt es sich z. B. mit\n"
            f"flatpak install flathub {auftrag.FONTFORGE_FLATPAK}\n"
            "oder\napt install fontforge",
            parent=self.fenster)

    def ordner_oeffnen(self) -> None:
        subprocess.Popen(["xdg-open", str(Path(self.sfd_auswahl.get()).parent)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    fenster = tk.Tk(className="Kritzelei")
    Oberflaeche(fenster)
    fenster.mainloop()
    return 0
