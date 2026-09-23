#!/usr/bin/env python3
"""Remplace l'embase JTAG cTBP 10 points par un Tag-Connect TC2050.

La specification est passee au TC2050 (spec-devkit.md section 4). Le devkit B
l'a recu a la main ; ce script porte le meme changement sur le devkit A, pour
que les deux cartes gardent les memes composants.

Le brochage repris est celui, verifie, du devkit B — c'est-a-dire le standard
TI 10 points. Les trois broches libres le restent : sur ce composant il n'y a
pas de TRSTn (SPRSPC5 section 5.3), et le rappel de 2,2 kOhms sur TMS en tient
lieu.

    python gen_jtag.py devkit_A_F280037.kicad_sch

Idempotent : si le TC2050 est deja pose, le script ne fait rien.
"""

import argparse
import re
from pathlib import Path

from kicad_gen import refuser_si_kicad_ouvert
from gen_composants import (
    LABEL_DIR, esc, instance, label, lib_symbol, pin_positions, sexp_block,
)

ANCIEN = "C2000_Devkit_Connectors:JTAG_CTBP_10"
NOUVEAU = "Connector:TC2050"
EMPREINTE = "Connector:Tag-Connect_TC2050-IDC-NL_2x05_P1.27mm_Vertical"

# Brochage releve sur le devkit B. Les broches 6, 8 et 9 restent libres.
NETS = {
    "1": "GND",
    "2": "JTAG_TCK",
    "3": "JTAG_TDO",
    "4": "JTAG_TMS",
    "5": "JTAG_TDI",
    "7": "~{nRESET}",
    "10": "VDDIO",
}

POSITION = (62.23, 199.39)   # meme emplacement que sur le devkit B

LIB_ID = re.compile(r'\(symbol\s*\n?\s*\(lib_id "([^"]+)"')
LABEL_RE = re.compile(r'\(global_label\s+"([^"]*)"[\s\S]{0,140}?'
                      r'\(at ([\d.-]+) ([\d.-]+)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("schema", type=Path)
    args = ap.parse_args()
    refuser_si_kicad_ouvert(args.schema)

    text = args.schema.read_text(encoding="utf-8")
    if NOUVEAU in text:
        print("%s : TC2050 deja pose" % args.schema.name)
        return

    # -- reperer l'ancienne embase et ses etiquettes ------------------------
    spot = next((m for m in LIB_ID.finditer(text) if m.group(1) == ANCIEN), None)
    if spot is None:
        raise SystemExit("%s introuvable dans %s" % (ANCIEN, args.schema.name))
    bloc = sexp_block(text, spot.start())
    at = re.search(r'\(at ([\d.-]+) ([\d.-]+)', bloc)
    ox, oy = float(at.group(1)), float(at.group(2))

    lib = args.schema.resolve().parent / "lib/C2000_Devkit_Connectors.kicad_sym"
    src = lib.read_text(encoding="utf-8")
    m = re.search(r'^\s{0,4}\(symbol "JTAG_CTBP_10"', src, re.M)
    anciennes = pin_positions(sexp_block(src, m.start()))

    # Les etiquettes ne sont rattachees a rien : elles coincident avec le point
    # de connexion. C'est cette coincidence qui les identifie.
    cibles = {(round(ox + dx, 2), round(oy - dy, 2))
              for dx, dy, _a in anciennes.values()}

    retires = 0
    for m in reversed(list(LABEL_RE.finditer(text))):
        pos = (round(float(m.group(2)), 2), round(float(m.group(3)), 2))
        if pos not in cibles:
            continue
        blk = sexp_block(text, m.start())
        text = text[:m.start()] + text[m.start() + len(blk):]
        retires += 1

    # -- retirer l'instance, puis sa definition si plus personne ne l'utilise
    spot = next(m for m in LIB_ID.finditer(text) if m.group(1) == ANCIEN)
    bloc = sexp_block(text, spot.start())
    text = text[:spot.start()] + text[spot.start() + len(bloc):]
    if ANCIEN not in [m.group(1) for m in LIB_ID.finditer(text)]:
        d = re.search(r'\n\s*\(symbol "%s"' % re.escape(ANCIEN), text)
        if d:
            blk = sexp_block(text, d.start() + 1)
            text = text[:d.start()] + text[d.start() + 1 + len(blk):]

    # -- poser le TC2050 ----------------------------------------------------
    defn = lib_symbol(NOUVEAU)
    a = text.index("(lib_symbols") + len("(lib_symbols")
    text = text[:a] + "\n" + defn + text[a:]

    project = args.schema.stem
    sch_uuid = re.search(r'\(uuid "([^"]+)"\)', text).group(1)
    geom = pin_positions(defn)
    x, y = POSITION
    parts = [instance("J3", NOUVEAU, "TC2050", EMPREINTE, x, y,
                      geom, project, sch_uuid)]
    for num, net in NETS.items():
        dx, dy, ang = geom[num]
        parts.append(label(net, x + dx, y - dy, ang))

    close = text.rstrip().rfind(")")
    text = text[:close] + "\n".join(parts) + "\n" + text[close:]
    args.schema.write_text(text, encoding="utf-8")

    print("%s :" % args.schema.name)
    print("   retire  %s et ses %d etiquettes" % (ANCIEN.split(":")[1], retires))
    print("   pose    J3 %s en (%.2f, %.2f)" % (NOUVEAU, x, y))
    for num in sorted(NETS, key=int):
        print("      pin %-3s -> %s" % (num, NETS[num]))
    print("   broches 6, 8 et 9 laissees libres")


if __name__ == "__main__":
    main()
