#!/usr/bin/env python3
"""Monte les deux projets KiCad des devkits a partir de imports/.

Les schemas viennent tout faits de imports/ : ce script ne les fabrique pas,
il les installe a la racine du depot (imports/ est ignore par git) et leur
ajoute le .kicad_pro et le .kicad_pcb qui manquent pour former un projet.

Le champ (project "...") des instances est reecrit au nom reel du projet :
les deux schemas fournis portent tous les deux "devkit_c2000", alors qu'ils
donnent deux projets distincts.

    python devkit_gen.py [--force]
"""

import argparse
import importlib.util
import json
import re
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "projet_gen", Path(__file__).with_name("projet_gen.py")
)
pg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pg)

IMPORTS = Path("imports")
LIBDIR = Path("lib")

# Les schemas fournis referencent ces deux nicknames de librairie.
LIBS = {
    "C2000_MCU": LIBDIR / "C2000_MCU.kicad_sym",
    "C2000_Devkit_Connectors": LIBDIR / "C2000_Devkit_Connectors.kicad_sym",
}

PROJECTS = [
    ("devkit_c2000_A_F280037", IMPORTS / "devkit_c2000_A_F280037.kicad_sch"),
    ("devkit_c2000_B_F28P551", IMPORTS / "devkit_c2000_B_F28P551.kicad_sch"),
]

# Contour provisoire : la rangee B fait 32 positions au pas 2,54, soit plus de
# 80 mm a elle seule. La dimension definitive sortira du placement.
BOARD_W = 90.0
BOARD_H = 45.0


def install_sch(name, src):
    text = src.read_text(encoding="utf-8")
    return re.sub(r'\(project "[^"]*"', '(project "%s"' % name, text)


def update_lib_table(out):
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
            '(descr "Devkit C2000"))\n' % (nick, path.as_posix())
        ) + ")\n"
        added.append(nick)
    table.write_text(text, encoding="utf-8")
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=".")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    for name, src in PROJECTS:
        if not src.exists():
            raise SystemExit("introuvable : %s" % src)
        for ext in (".kicad_sch", ".kicad_pcb", ".kicad_pro"):
            p = out / (name + ext)
            if p.exists() and not args.force:
                raise SystemExit("%s existe deja — utiliser --force" % p)

    old = pg.BOARD_W, pg.BOARD_H
    pg.BOARD_W, pg.BOARD_H = BOARD_W, BOARD_H
    try:
        for name, src in PROJECTS:
            (out / (name + ".kicad_sch")).write_text(
                install_sch(name, src), encoding="utf-8"
            )
            (out / (name + ".kicad_pcb")).write_text(
                pg.gen_pcb(), encoding="utf-8"
            )
            pro = pg.gen_pro()
            pro["meta"]["filename"] = name + ".kicad_pro"
            (out / (name + ".kicad_pro")).write_text(
                json.dumps(pro, indent=2), encoding="utf-8"
            )
            print("Ecrit : %s.kicad_sch / .kicad_pcb / .kicad_pro" % name)
    finally:
        pg.BOARD_W, pg.BOARD_H = old

    added = update_lib_table(out)
    print("sym-lib-table : %s" % (", ".join(added) if added else "deja a jour"))


if __name__ == "__main__":
    main()
