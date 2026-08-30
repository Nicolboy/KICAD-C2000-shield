#!/usr/bin/env python3
"""
connecteur_gen.py — le fichier de brochage Markdown est la source de verite.

Lit connecteur-2x24.md et produit :
  1. CONN_C2000_2x24.kicad_sym  — symbole KiCad 48 broches, noms et numeros corrects
  2. brochage.csv               — table a plat, pour la doc et la revue
  3. rapport.txt                — verifications automatiques (retour non nul si echec)

Usage :
    python3 connecteur_gen.py connecteur-2x24.md -o build/
    python3 connecteur_gen.py connecteur-2x24.md --check     # verifications seules

Regle du projet : on ne modifie JAMAIS le .kicad_sym a la main. On modifie le .md
et on regenere. Sinon les deux divergent et la source de verite est perdue.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

VERSION = "1.0"

# --------------------------------------------------------------------------
# Modele
# --------------------------------------------------------------------------


@dataclass
class Pin:
    pos: str  # "A1", "B17"
    row: str  # "A" ou "B"
    index: int  # 1..24
    signal: str  # nom nettoye, sans gras Markdown
    mcu_pin: str | None = None  # broche du boitier, ex "9"
    gpio: str | None = None  # "GPIO18" (rangee B seulement)
    mux: str | None = None  # "1" (rangee B seulement)
    note: str = ""  # ex "CMP1_HP0", "XRSn"
    etype: str = "passive"  # type electrique KiCad


# Type electrique deduit du nom de signal. L'ordre compte : premiere regle qui
# matche l'emporte.
ETYPE_RULES: list[tuple[str, str]] = [
    (r"^GND$", "power_in"),
    (r"^\+5V$", "power_in"),
    (r"^VREF_ADC$", "passive"),
    (r"^I_SHUNT", "passive"),
    (r"^ADC_", "passive"),
    (r"^nRESET$", "input"),
    (r"^UART_RX$", "input"),
    (r"^UART_TX$", "output"),
    (r"^SPI_SOMI$", "input"),
    (r"^SPI_SIMO$", "output"),
    (r"^SPI_CLK$", "output"),
    (r"^SPI_STE$", "output"),
    (r"^I2C_", "bidirectional"),
    (r"^CMP_OUT$", "output"),
    (r"^CLB_OUT$", "output"),
    (r"^PWM", "output"),
    (r"^GPIO_", "bidirectional"),
]


def deduce_etype(signal: str) -> str:
    for pattern, etype in ETYPE_RULES:
        if re.match(pattern, signal):
            return etype
    return "passive"


# --------------------------------------------------------------------------
# Analyse du Markdown
# --------------------------------------------------------------------------

DASHES = "\u2014\u2013-"  # em dash, en dash, tiret


def clean(cell: str) -> str:
    """Retire le gras Markdown, les espaces, et normalise les tirets en None."""
    c = cell.strip()
    c = re.sub(r"\*\*(.+?)\*\*", r"\1", c)
    c = re.sub(r"\*(.+?)\*", r"\1", c)
    c = c.replace("`", "").strip()
    return c


def split_pin_and_note(cell: str) -> tuple[str | None, str]:
    """'9 (CMP1_HP0)' -> ('9', 'CMP1_HP0').  '—' -> (None, '')."""
    c = clean(cell)
    if not c or c in DASHES:
        return None, ""
    note = ""
    m = re.search(r"\(([^)]*)\)", c)
    if m:
        note = m.group(1).strip()
        c = c[: m.start()].strip()
    if not c or c in DASHES:
        return None, note
    return c, note


def table_rows(md: str, heading: str) -> list[list[str]]:
    """Extrait les lignes de donnees du premier tableau suivant un titre."""
    lines = md.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if ln.startswith("##") and heading in ln), None
    )
    if start is None:
        raise ValueError(f"section introuvable : {heading!r}")
    rows: list[list[str]] = []
    in_table = False
    for ln in lines[start + 1 :]:
        if ln.startswith("##"):
            break
        if not ln.strip().startswith("|"):
            if in_table:
                break
            continue
        cells = [c for c in ln.strip().strip("|").split("|")]
        if all(set(c.strip()) <= set("-: ") for c in cells):  # separateur
            in_table = True
            continue
        if in_table:
            rows.append(cells)
    return rows


def parse_row_a(md: str) -> list[Pin]:
    """Rangee A : 6 colonnes, deux demi-tables cote a cote."""
    pins: list[Pin] = []
    for cells in table_rows(md, "Rangée A"):
        if len(cells) < 6:
            continue
        for pos_c, sig_c, pin_c in ((cells[0], cells[1], cells[2]),
                                    (cells[3], cells[4], cells[5])):
            pos = clean(pos_c)
            if not re.fullmatch(r"A\d+", pos):
                continue
            mcu, note = split_pin_and_note(pin_c)
            sig = clean(sig_c)
            pins.append(
                Pin(pos=pos, row="A", index=int(pos[1:]), signal=sig,
                    mcu_pin=mcu, note=note, etype=deduce_etype(sig))
            )
    return sorted(pins, key=lambda p: p.index)


def parse_row_b(md: str) -> list[Pin]:
    """Rangee B : 10 colonnes, deux demi-tables de 5."""
    pins: list[Pin] = []
    for cells in table_rows(md, "Rangée B"):
        if len(cells) < 10:
            continue
        for half in (cells[0:5], cells[5:10]):
            pos = clean(half[0])
            if not re.fullmatch(r"B\d+", pos):
                continue
            sig = clean(half[1])
            gpio = clean(half[2])
            gpio = None if not gpio or gpio in DASHES else gpio
            mcu, note = split_pin_and_note(half[3])
            mux = clean(half[4])
            mux = None if not mux or mux in DASHES else mux
            pins.append(
                Pin(pos=pos, row="B", index=int(pos[1:]), signal=sig,
                    mcu_pin=mcu, gpio=gpio, mux=mux, note=note,
                    etype=deduce_etype(sig))
            )
    return sorted(pins, key=lambda p: p.index)


# --------------------------------------------------------------------------
# Verifications
# --------------------------------------------------------------------------


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    def err(self, m: str) -> None:
        self.errors.append(m)

    def warn(self, m: str) -> None:
        self.warnings.append(m)

    def info(self, m: str) -> None:
        self.infos.append(m)

    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        out = [f"Rapport de verification — connecteur_gen {VERSION}", "=" * 52, ""]
        for label, items in (
            ("ERREUR ", self.errors),
            ("ATTENTION", self.warnings),
            ("info   ", self.infos),
        ):
            for m in items:
                out.append(f"[{label}] {m}")
        out.append("")
        out.append(
            f"{len(self.errors)} erreur(s), {len(self.warnings)} attention(s)."
        )
        out.append("RESULTAT : " + ("OK" if self.ok() else "ECHEC"))
        return "\n".join(out)


# Signaux dont l'isolation par masse est une exigence de conception.
# Formulee dans le .md : « masse isolante de part et d'autre de chaque I_SHUNT
# et de VREF_ADC ». C'est cette phrase que le test ci-dessous rend executable.
ISOLATION_REQUISE = ("I_SHUNT1", "I_SHUNT2", "VREF_ADC")

# Positions dont le double usage est un choix de conception a ne pas defaire.
DOUBLE_USAGE = {"B10", "B11", "B12", "B13"}


def verifier(row_a: list[Pin], row_b: list[Pin], rep: Report) -> None:
    all_pins = row_a + row_b

    # -- completude des rangees ------------------------------------------
    for name, row in (("A", row_a), ("B", row_b)):
        if len(row) != 24:
            rep.err(f"rangee {name} : {len(row)} positions au lieu de 24")
        manquantes = set(range(1, 25)) - {p.index for p in row}
        if manquantes:
            rep.err(
                f"rangee {name} : positions manquantes "
                + ", ".join(f"{name}{i}" for i in sorted(manquantes))
            )

    # -- unicite des broches du boitier ----------------------------------
    vus: dict[str, list[str]] = {}
    for p in all_pins:
        if p.mcu_pin and "/" not in p.mcu_pin and p.mcu_pin.isdigit():
            vus.setdefault(p.mcu_pin, []).append(p.pos)
    for broche, positions in sorted(vus.items(), key=lambda kv: int(kv[0])):
        if len(positions) > 1:
            rep.err(
                f"broche {broche} du MCU exportee sur plusieurs positions : "
                + ", ".join(positions)
            )

    # -- unicite des GPIO -------------------------------------------------
    gvus: dict[str, list[str]] = {}
    for p in row_b:
        if p.gpio:
            gvus.setdefault(p.gpio, []).append(p.pos)
    for gpio, positions in gvus.items():
        if len(positions) > 1:
            rep.err(f"{gpio} affecte a plusieurs positions : " + ", ".join(positions))

    # -- unicite des noms de signaux (hors GND) ---------------------------
    svus: dict[str, list[str]] = {}
    for p in all_pins:
        if p.signal != "GND":
            svus.setdefault(p.signal, []).append(p.pos)
    for sig, positions in svus.items():
        if len(positions) > 1:
            rep.err(f"signal {sig} en double : " + ", ".join(positions))

    # -- isolation par masse ----------------------------------------------
    par_pos = {p.pos: p for p in all_pins}
    for p in all_pins:
        if p.signal not in ISOLATION_REQUISE:
            continue
        for voisin_idx in (p.index - 1, p.index + 1):
            if not 1 <= voisin_idx <= 24:
                rep.warn(
                    f"{p.pos} ({p.signal}) est en bout de rangee : pas de masse "
                    "isolante d'un cote"
                )
                continue
            voisin = par_pos.get(f"{p.row}{voisin_idx}")
            if voisin is None or voisin.signal != "GND":
                got = voisin.signal if voisin else "?"
                rep.err(
                    f"{p.pos} ({p.signal}) : voisin {p.row}{voisin_idx} = {got}, "
                    "masse isolante attendue"
                )

    # -- densite de masse rangee A ----------------------------------------
    gnd_a = [p.index for p in row_a if p.signal == "GND"]
    ecarts = [b - a for a, b in zip(gnd_a, gnd_a[1:])]
    if ecarts and max(ecarts) > 3:
        rep.warn(
            f"rangee A : jusqu'a {max(ecarts) - 1} signaux consecutifs sans masse "
            "intercalee (regle annoncee : masse toutes les deux lignes)"
        )

    # -- double usage B10-B13 ---------------------------------------------
    for pos in sorted(DOUBLE_USAGE):
        p = par_pos.get(pos)
        if p is None:
            rep.err(f"{pos} absente : le double usage GPIO/HRPWM est perdu")
        elif not p.signal.startswith("GPIO_"):
            rep.err(
                f"{pos} porte {p.signal} au lieu d'un GPIO generique : le double "
                "usage EPWM3/EPWM4 de reserve est perdu. Choix de conception "
                "volontaire, ne pas defaire sans decision explicite."
            )

    # -- decomptes informatifs ---------------------------------------------
    n_gnd = sum(1 for p in all_pins if p.signal == "GND")
    n_adc = sum(1 for p in all_pins if p.signal.startswith("ADC_"))
    rep.info(f"{len(all_pins)} positions, {n_gnd} masses")
    rep.info(f"{n_adc} voies ADC simples (besoin du shield : 7, marge {n_adc - 7})")
    rep.info(
        "broches du MCU exportees : "
        + ", ".join(str(b) for b in sorted(map(int, vus)))
    )


# --------------------------------------------------------------------------
# Sortie : symbole KiCad
# --------------------------------------------------------------------------

PITCH = 2.54
BODY_W = 33.02


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def pin_sexpr(p: Pin, x: float, y: float, angle: int) -> str:
    nom = p.signal
    if p.gpio:
        nom = f"{p.signal}"  # le GPIO va en champ, pas dans le nom
    return (
        f'\t\t\t(pin {p.etype} line (at {x:.2f} {y:.2f} {angle}) (length 5.08)\n'
        f'\t\t\t\t(name "{esc(nom)}" (effects (font (size 1.27 1.27))))\n'
        f'\t\t\t\t(number "{p.pos}" (effects (font (size 1.27 1.27))))\n'
        f"\t\t\t)"
    )


def build_symbol(row_a: list[Pin], row_b: list[Pin], name: str) -> str:
    half = (24 - 1) * PITCH / 2
    top = half + PITCH
    bot = -half - PITCH
    left = -BODY_W / 2
    right = BODY_W / 2

    parts: list[str] = []
    parts.append("(kicad_symbol_lib")
    parts.append("\t(version 20241209)")
    parts.append(f'\t(generator "connecteur_gen")')
    parts.append(f'\t(generator_version "{VERSION}")')
    parts.append(f'\t(symbol "{name}"')
    parts.append("\t\t(pin_names (offset 0.508))")
    parts.append("\t\t(exclude_from_sim no)")
    parts.append("\t\t(in_bom yes)")
    parts.append("\t\t(on_board yes)")
    parts.append(
        f'\t\t(property "Reference" "J" (at {left:.2f} {top + 2.54:.2f} 0)'
        ' (effects (font (size 1.27 1.27)) (justify left)))'
    )
    parts.append(
        f'\t\t(property "Value" "{name}" (at {left:.2f} {bot - 2.54:.2f} 0)'
        ' (effects (font (size 1.27 1.27)) (justify left)))'
    )
    parts.append(
        '\t\t(property "Footprint" "Connector_PinHeader_2.54mm:'
        'PinHeader_2x24_P2.54mm_Vertical" (at 0 0 0)'
        ' (effects (font (size 1.27 1.27)) (hide yes)))'
    )
    parts.append(
        '\t\t(property "Description" "Connecteur devkit C2000 2x24 — genere depuis'
        ' connecteur-2x24.md, ne pas editer a la main"'
        ' (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'
    )
    parts.append(f'\t\t(symbol "{name}_1_1"')
    parts.append(
        f"\t\t\t(rectangle (start {left:.2f} {top:.2f}) (end {right:.2f} {bot:.2f})\n"
        "\t\t\t\t(stroke (width 0.254) (type default))\n"
        "\t\t\t\t(fill (type background))\n"
        "\t\t\t)"
    )
    for p in row_a:  # rangee A a gauche
        y = half - (p.index - 1) * PITCH
        parts.append(pin_sexpr(p, left - 5.08, y, 0))
    for p in row_b:  # rangee B a droite
        y = half - (p.index - 1) * PITCH
        parts.append(pin_sexpr(p, right + 5.08, y, 180))
    parts.append("\t\t)")
    parts.append("\t)")
    parts.append(")")
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------
# Sortie : CSV
# --------------------------------------------------------------------------


def write_csv(pins: list[Pin], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pos", "rangee", "signal", "broche_mcu", "gpio", "mux",
                    "note", "type_electrique"])
        for p in pins:
            w.writerow([p.pos, p.row, p.signal, p.mcu_pin or "", p.gpio or "",
                        p.mux or "", p.note, p.etype])


# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="fichier Markdown de brochage")
    ap.add_argument("-o", "--outdir", type=Path, default=Path("build"))
    ap.add_argument("--name", default="CONN_C2000_2x24", help="nom du symbole")
    ap.add_argument("--check", action="store_true",
                    help="verifications seules, aucun fichier ecrit")
    args = ap.parse_args()

    md = args.source.read_text(encoding="utf-8")
    row_a = parse_row_a(md)
    row_b = parse_row_b(md)

    rep = Report()
    verifier(row_a, row_b, rep)
    print(rep.render())

    if args.check:
        return 0 if rep.ok() else 1

    if not rep.ok():
        print("\nGeneration annulee : corrigez le .md d'abord.", file=sys.stderr)
        return 1

    args.outdir.mkdir(parents=True, exist_ok=True)
    sym = args.outdir / f"{args.name}.kicad_sym"
    sym.write_text(build_symbol(row_a, row_b, args.name), encoding="utf-8")
    csv_path = args.outdir / "brochage.csv"
    write_csv(row_a + row_b, csv_path)
    (args.outdir / "rapport.txt").write_text(rep.render() + "\n", encoding="utf-8")

    print(f"\nEcrit : {sym}")
    print(f"Ecrit : {csv_path}")
    print(f"Ecrit : {args.outdir / 'rapport.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
