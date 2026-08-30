#!/usr/bin/env python3
"""Genere le projet KiCad du shield sur le connecteur 2 x 24.

Source de verite : doc/brochage-2x24.md -> gen_symbole_2x24.py ->
build/*.kicad_sym. Ce script assemble shield_2x24.kicad_sch / .kicad_pcb /
.kicad_pro autour de ce symbole.

Brochage anterieur a celui du 2026-08-30 : conserve tel quel, le projet
courant est gen_shield.py.
"""

import argparse
import json
import re
from pathlib import Path

from kicad_gen import (
    POWER_LIB,
    STUB,
    extract_from,
    gen_pcb,
    gen_pro,
    indent,
    parse_pins,
    pwr_symbol,
    uid,
    wire,
)

PROJECT = "shield_2x24"
LIB_NICK = "shield"
SYM_NAME = "CONN_C2000_2x24"
def extract_symbol(lib_text):
    """Retourne le bloc (symbol "NOM" ...) complet du .kicad_sym."""
    start = lib_text.index('(symbol "%s"' % SYM_NAME)
    depth = 0
    for i in range(start, len(lib_text)):
        c = lib_text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return lib_text[start : i + 1]
    raise ValueError("bloc symbole non termine")


def qualify(block):
    """Prefixe le nom du symbole par le nickname de librairie.

    Seul le symbole parent est prefixe : dans lib_symbols, les sous-symboles
    d'unite gardent leur nom nu (cf. "Device:R" -> "R_1_1" en KiCad 10).
    """
    return block.replace(
        '(symbol "%s"' % SYM_NAME, '(symbol "%s:%s"' % (LIB_NICK, SYM_NAME), 1
    )


def gen_power(pins, at_x, at_y, sch_uuid):
    """Fils + symboles d'alimentation sur chaque broche GND et +5V.

    La broche est en (at_x + px, at_y - py) : l'axe Y du schema est inverse
    par rapport a celui du symbole. Un fil horizontal de STUB part vers
    l'exterieur du boitier, le symbole d'alimentation est pose au bout.
    """
    items, insts, n = [], [], 0
    flagged = set()
    for num, name, px, py, ang in pins:
        if name not in ("GND", "+5V"):
            continue
        n += 1
        # angle 0 : broche a gauche, le fil part vers -X. angle 180 : vers +X.
        direction = -1 if ang == 0 else 1
        x0 = at_x + px
        y0 = at_y - py

        # J1 declare GND et +5V en power_in : sans source power_out sur le
        # net, l'ERC leve power_pin_not_driven. Le connecteur est bien la
        # source d'alimentation de la carte, mais le brochage — qui fait
        # autorite — le decrit en entree. Un PWR_FLAG le dit a l'ERC sans
        # toucher au type electrique des broches. Un seul par net suffit :
        # pose sur la premiere broche rencontree, au milieu d'un stub double,
        # le symbole d'alimentation restant au bout.
        first = name not in flagged
        flagged.add(name)
        x1 = x0 + direction * (STUB * 2 if first else STUB)
        if first:
            # Le stub est coupe en deux au point du flag : un pin pose au
            # milieu d'un fil continu ne se connecte pas, il lui faut une
            # extremite de segment et une jonction.
            xm = x0 + direction * STUB
            items.append(wire(x0, y0, xm, y0))
            items.append(wire(xm, y0, x1, y0))
            items.append(
                '\t(junction (at %.2f %.2f) (diameter 0) (color 0 0 0 0)'
                ' (uuid "%s"))' % (xm, y0, uid())
            )
            items.append(
                pwr_symbol(
                    "PWR_FLAG", "#FLG%02d" % n, xm, y0, 0, sch_uuid, PROJECT,
                    show_value=False,
                )
            )
        else:
            items.append(wire(x0, y0, x1, y0))
        ref = "#PWR%02d" % n
        rot = 270 if direction < 0 else 90
        items.append(
            pwr_symbol(name, ref, x1, y0, rot, sch_uuid, PROJECT,
                       direction=direction)
        )
        insts.append(ref)
    return items, insts


def gen_sch(sym_block, ref="J1"):
    sch_uuid = uid()
    sym_uuid = uid()
    # Le symbole est dessine centre sur son origine ; on le pose sur la feuille.
    # Multiples de 1,27 mm : sinon toutes les extremites de fil tombent hors
    # grille et l'ERC leve endpoint_off_grid sur chacune.
    at_x, at_y = 127.0, 101.6

    pins = re.findall(r'\(number "([^"]+)"', sym_block)
    pin_uuids = "\n".join(
        '\t\t\t(pin "%s" (uuid "%s"))' % (n, uid()) for n in pins
    )

    # Alimentations : un symbole power par broche GND et +5V du connecteur.
    pwr_lib = "\n".join(
        extract_from(POWER_LIB, n) for n in ("GND", "+5V", "PWR_FLAG")
    )
    pwr_items, _ = gen_power(parse_pins(sym_block), at_x, at_y, sch_uuid)

    return """(kicad_sch
\t(version 20241209)
\t(generator "gen_shield_2x24")
\t(generator_version "1.0")
\t(uuid "%s")
\t(paper "A4")
\t(title_block
\t\t(title "Shield d'isolation C2000 — connecteur 2 x 24")
\t\t(comment 1 "Brochage genere depuis connecteur-2x24.md — ne pas editer a la main")
\t)
\t(lib_symbols
%s
\t)
\t(symbol
\t\t(lib_id "%s:%s")
\t\t(at %.2f %.2f 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "%s")
\t\t(property "Reference" "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Value" "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Footprint" "Connector_PinHeader_2.54mm:PinHeader_2x24_P2.54mm_Vertical" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (hide yes)))
%s
\t\t(instances
\t\t\t(project "shield_2x24"
\t\t\t\t(path "/%s" (reference "%s") (unit 1))
\t\t\t)
\t\t)
\t)
%s
\t(sheet_instances
\t\t(path "/" (page "1"))
\t)
)
""" % (
        sch_uuid,
        indent(sym_block, 2) + "\n" + indent(pwr_lib, 2),
        LIB_NICK,
        SYM_NAME,
        at_x,
        at_y,
        sym_uuid,
        ref,
        at_x - 16.51,
        at_y - 34.29,
        SYM_NAME,
        at_x - 16.51,
        at_y + 34.29,
        at_x,
        at_y,
        pin_uuids,
        sch_uuid,
        ref,
        "\n".join(pwr_items),
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="build/CONN_C2000_2x24.kicad_sym")
    ap.add_argument("-o", "--out", default=".")
    ap.add_argument("--name", default="shield_2x24")
    ap.add_argument(
        "--force", action="store_true", help="ecrase un projet existant"
    )
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sch_path = out / (args.name + ".kicad_sch")
    pcb_path = out / (args.name + ".kicad_pcb")
    pro_path = out / (args.name + ".kicad_pro")
    for p in (sch_path, pcb_path, pro_path):
        if p.exists() and not args.force:
            raise SystemExit(
                "%s existe deja — refus d'ecraser (utiliser --force)" % p
            )

    lib_text = Path(args.sym).read_text(encoding="utf-8")
    sym_block = qualify(extract_symbol(lib_text))

    sch_path.write_text(gen_sch(sym_block), encoding="utf-8")
    pcb_path.write_text(gen_pcb(), encoding="utf-8")
    pro_path.write_text(json.dumps(gen_pro(args.name), indent=2), encoding="utf-8")

    lib_dir = Path(args.sym).parent.as_posix()
    # La table est partagee avec les autres projets du depot : on ajoute son
    # entree si elle manque, on ne reecrit jamais le fichier entier.
    table = out / "sym-lib-table"
    entry = (
        '  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s")(options "")'
        '(descr "Connecteur genere"))\n' % (LIB_NICK, Path(args.sym).as_posix())
    )
    if table.exists():
        text = table.read_text(encoding="utf-8")
        if '(name "%s")' % LIB_NICK not in text:
            table.write_text(
                text.rstrip().rstrip(")").rstrip() + "\n" + entry + ")\n",
                encoding="utf-8",
            )
    else:
        table.write_text(
            "(sym_lib_table\n  (version 7)\n" + entry + ")\n", encoding="utf-8"
        )

    print("Ecrit : %s" % sch_path)
    print("Ecrit : %s" % pcb_path)
    print("Ecrit : %s" % pro_path)
    print("Ecrit : %s" % (out / "sym-lib-table"))
    print("Librairie %s -> %s" % (LIB_NICK, lib_dir))


if __name__ == "__main__":
    main()
