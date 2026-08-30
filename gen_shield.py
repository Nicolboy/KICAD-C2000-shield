#!/usr/bin/env python3
"""Genere le projet KiCad du shield depuis les symboles de lib/.

Source : doc/brochage-devkit.md, doc/README-lib.md et doc/README-esp32.md.
Deux rangees devkit de 28 positions, quatre nappes 2 x 8, alimentation sur
connecteur separe, et les deux embases 1 x 16 de l'ESP32-C6-DevKitC-1.

Le schema pose les connecteurs et cable les deux nets d'alimentation. Le
routage des signaux n'est pas fait ici : il demande des choix de conception
qui n'appartiennent pas a un generateur.

    python gen_shield.py [-o .] [--name shield] [--force]
"""

import argparse
import json
import re
from pathlib import Path

import kicad_gen as pg

IMPORTS = Path("imports")
LIBDIR = Path("lib")

# Une librairie par famille de connecteurs, chacune avec son nickname.
LIBS = {
    "C2000_Devkit_Connectors": LIBDIR / "C2000_Devkit_Connectors.kicad_sym",
    "ESP32_C6_Devkit": LIBDIR / "ESP32_C6_Devkit.kicad_sym",
}

# Carte A2 : dix connecteurs, dont deux rangees de 28 et les deux embases de
# l'ESP32, ne tiennent pas sur A3.
PAPER = "A2"

# Nom du projet, repris dans les instances de chaque symbole.
PROJECT = "shield"

# (librairie, symbole, reference, x, y) — coordonnees multiples de 1,27 mm,
# sinon les extremites de fil tombent hors grille et l'ERC leve
# endpoint_off_grid sur chacune.
#
# J9 et J10 sont les deux supports 1 x 16 qui recoivent l'ESP32-C6-DevKitC-1
# directement, sans carte intermediaire (cf. doc/README-lib.md, "Montage sur
# le shield").
C2000 = "C2000_Devkit_Connectors"
ESP32 = "ESP32_C6_Devkit"

PLACEMENT = [
    (C2000, "DEVKIT_C2000_ROW_A", "J1", 76.2, 116.84),
    (C2000, "DEVKIT_C2000_ROW_B", "J2", 177.8, 116.84),
    (C2000, "NAPPE_ADC1", "J3", 279.4, 63.5),
    (C2000, "NAPPE_ADC2", "J4", 279.4, 139.7),
    (C2000, "NAPPE_PWM", "J5", 279.4, 215.9),
    (C2000, "NAPPE_GPIO", "J6", 375.92, 63.5),
    (C2000, "ALIM_5V", "J7", 375.92, 139.7),
    (C2000, "ALIM_5V", "J8", 375.92, 177.8),
    (ESP32, "ESP32_C6_DEVKITC_1_J1", "J9", 468.63, 63.5),
    (ESP32, "ESP32_C6_DEVKITC_1_J3", "J10", 468.63, 139.7),
]

# Contour : le shield porte les deux devkits cote a cote plus quatre embases
# de nappe. Dimension a confirmer une fois les empreintes placees.
BOARD_W = 100.0
BOARD_H = 80.0


def sym_blocks(path):
    """{nom: bloc} des symboles de premier niveau d'une librairie."""
    text = Path(path).read_text(encoding="utf-8")
    starts = [
        (m.start(), m.group(1))
        for m in re.finditer(r'^\s{0,2}\(symbol "([^"]+)"', text, re.M)
    ]
    out = {}
    for s, name in starts:
        depth = 0
        for i in range(s, len(text)):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    out[name] = text[s : i + 1]
                    break
        else:
            raise ValueError("bloc symbole %s non termine" % name)
    return out


def qualified(block, nick, name):
    return block.replace(
        '(symbol "%s"' % name, '(symbol "%s:%s"' % (nick, name), 1
    )


def conn_instance(nick, name, ref, x, y, sch_uuid, pins):
    pin_uuids = "\n".join(
        '\t\t(pin "%s" (uuid "%s"))' % (n, pg.uid()) for n, _, _, _, _ in pins
    )
    return (
        '\t(symbol\n'
        '\t\t(lib_id "%s:%s")\n'
        '\t\t(at %.2f %.2f 0)\n'
        '\t\t(unit 1)\n'
        '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n'
        '\t\t(uuid "%s")\n'
        '\t\t(property "Reference" "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
        '\t\t(property "Value" "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
        '%s\n'
        '\t\t(instances\n'
        '\t\t\t(project "%s"\n'
        '\t\t\t\t(path "/%s" (reference "%s") (unit 1))\n'
        '\t\t\t)\n'
        '\t\t)\n'
        '\t)'
        % (
            nick, name, x, y, pg.uid(), ref, x - 22.86, y - 45.72,
            name, x - 22.86, y + 45.72, pin_uuids, PROJECT, sch_uuid, ref,
        )
    )


def gen_sch():
    sch_uuid = pg.uid()
    blocks = {nick: sym_blocks(path) for nick, path in LIBS.items()}

    # Un seul exemplaire de chaque symbole dans lib_symbols, meme si le
    # symbole est pose plusieurs fois — ALIM_5V l'est deux fois.
    used = []
    for nick, name, _ref, _x, _y in PLACEMENT:
        if (nick, name) not in used:
            used.append((nick, name))

    lib = "\n".join(
        pg.indent(qualified(blocks[nick][name], nick, name), 2)
        for nick, name in used
    )
    lib += "\n" + "\n".join(
        pg.indent(pg.extract_from(pg.POWER_LIB, n), 2)
        for n in ("GND", "+5V", "PWR_FLAG")
    )

    body, n_pwr = [], 0
    flagged = set()
    for nick, name, ref, x, y in PLACEMENT:
        pins = pg.parse_pins(blocks[nick][name])
        body.append(conn_instance(nick, name, ref, x, y, sch_uuid, pins))
        items, count = wire_power(pins, x, y, sch_uuid, n_pwr, flagged)
        body.extend(items)
        n_pwr += count

    return """(kicad_sch
\t(version 20241209)
\t(generator "gen_shield")
\t(generator_version "1.0")
\t(uuid "%s")
\t(paper "%s")
\t(title_block
\t\t(title "Shield d'isolation C2000 — devkits, nappes et ESP32-C6")
\t\t(comment 1 "Genere depuis lib/ — connecteur devkit 2 x 28")
\t\t(comment 2 "Signaux non cables : routage a faire a la main")
\t)
\t(lib_symbols
%s
\t)
%s
\t(sheet_instances
\t\t(path "/" (page "1"))
\t)
)
""" % (sch_uuid, PAPER, lib, "\n".join(body))


def wire_power(pins, at_x, at_y, sch_uuid, n0, flagged):
    """Stub + symbole d'alimentation sur chaque broche GND et +5V.

    Tous les pins des symboles importes sont a gauche (angle 0) : les stubs
    partent donc vers -X. Un PWR_FLAG unique par net, sur la premiere broche
    rencontree, parce que ces broches sont en power_in (cf. CLAUDE.md).
    """
    items, n = [], 0
    for num, name, px, py, ang in pins:
        if name not in ("GND", "+5V"):
            continue
        n += 1
        direction = -1 if ang == 0 else 1
        x0, y0 = at_x + px, at_y - py
        first = name not in flagged
        flagged.add(name)
        x1 = x0 + direction * (pg.STUB * 2 if first else pg.STUB)
        if first:
            xm = x0 + direction * pg.STUB
            items.append(pg.wire(x0, y0, xm, y0))
            items.append(pg.wire(xm, y0, x1, y0))
            items.append(
                '\t(junction (at %.2f %.2f) (diameter 0) (color 0 0 0 0)'
                ' (uuid "%s"))' % (xm, y0, pg.uid())
            )
            items.append(
                pg.pwr_symbol(
                    "PWR_FLAG", "#FLG%02d" % (n0 + n), xm, y0, 0, sch_uuid, PROJECT,
                    show_value=False,
                )
            )
        else:
            items.append(pg.wire(x0, y0, x1, y0))
        items.append(
            pg.pwr_symbol(
                name, "#PWR%03d" % (n0 + n), x1, y0,
                270 if direction < 0 else 90, sch_uuid, PROJECT,
                direction=direction,
            )
        )
    return items, n


def gen_pro(name):
    pro = pg.gen_pro(name)
    pro["meta"]["filename"] = name + ".kicad_pro"
    return pro


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=".")
    ap.add_argument("--name", default="shield")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        ext: out / (args.name + ext)
        for ext in (".kicad_sch", ".kicad_pcb", ".kicad_pro")
    }
    for p in paths.values():
        if p.exists() and not args.force:
            raise SystemExit("%s existe deja — utiliser --force" % p)

    old_w, old_h = pg.BOARD_W, pg.BOARD_H
    pg.BOARD_W, pg.BOARD_H = BOARD_W, BOARD_H
    paths[".kicad_pcb"].write_text(pg.gen_pcb(), encoding="utf-8")
    pg.BOARD_W, pg.BOARD_H = old_w, old_h

    paths[".kicad_sch"].write_text(gen_sch(), encoding="utf-8")
    paths[".kicad_pro"].write_text(
        json.dumps(gen_pro(args.name), indent=2), encoding="utf-8"
    )

    # La table est partagee avec les autres projets du depot : on ajoute les
    # entrees manquantes, on ne reecrit jamais le fichier entier.
    table = out / "sym-lib-table"
    text = (
        table.read_text(encoding="utf-8")
        if table.exists()
        else "(sym_lib_table\n  (version 7)\n)\n"
    )
    added = []
    for nick, path in LIBS.items():
        if '(name "%s")' % nick in text:
            continue
        text = text.rstrip().rstrip(")").rstrip() + "\n" + (
            '  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s")(options "")'
            '(descr "Connecteurs du shield"))\n' % (nick, path.as_posix())
        ) + ")\n"
        added.append(nick)
    table.write_text(text, encoding="utf-8")

    for p in paths.values():
        print("Ecrit : %s" % p)
    print("sym-lib-table : %s" % (", ".join(added) if added else "deja a jour"))


if __name__ == "__main__":
    main()
