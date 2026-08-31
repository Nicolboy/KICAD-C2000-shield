#!/usr/bin/env python3
"""Monte les deux projets KiCad des devkits a partir de imports/.

Les schemas viennent tout faits de imports/ : ce script ne les fabrique pas,
il les installe a la racine du depot (imports/ est ignore par git) et leur
ajoute le .kicad_pro et le .kicad_pcb qui manquent pour former un projet.

Deux retouches sont appliquees a chaque schema installe :

1. le champ (project "...") est reecrit au nom reel du projet —
   les deux fichiers portent "devkit_c2000" alors qu ils
   donnent deux projets distincts ;
2. le symbole MCU est remplace par sa version carree (gen_symbole_mcu.py) et
   les 64 etiquettes globales sont deplacees sur les nouvelles broches.

    python gen_devkit.py [--force]
"""

import argparse
import json
import re
from pathlib import Path

import kicad_gen as pg

IMPORTS = Path("imports")
LIBDIR = Path("lib")

MCU_NICK = "C2000_MCU"

# Le symbole MCU pose dans le schema est la version carree produite par
# gen_symbole_mcu.py, pas celle de lib/ : le nickname doit pointer sur elle,
# sinon l'ERC leve lib_symbol_mismatch a chaque ouverture.
MCU_LIB = Path("build/C2000_MCU_LQFP64.kicad_sym")

# Les schemas fournis referencent ces deux nicknames de librairie.
LIBS = {
    MCU_NICK: MCU_LIB,
    "C2000_Devkit_Connectors": LIBDIR / "C2000_Devkit_Connectors.kicad_sym",
}

PROJECTS = [
    ("devkit_A_F280037", IMPORTS / "devkit_c2000_A_F280037.kicad_sch"),
    ("devkit_B_F28P551", IMPORTS / "devkit_c2000_B_F28P551.kicad_sch"),
]

# Contour provisoire : chaque rangee fait 28 positions au pas 2,54, soit une
# carte de 71 mm de long (doc/README-lib.md). Dimension a confirmer.
BOARD_W = 90.0
BOARD_H = 45.0


# Orientation de l'etiquette globale selon l'angle du pin qu'elle touche.
# Le texte s'eloigne toujours du corps du symbole.
LABEL_DIR = {0: (180, "right"), 180: (0, "left"),
             90: (270, "right"), 270: (90, "left")}

LABEL_RE = re.compile(
    r'\(global_label "((?:[^"\\]|\\.)*)" \(shape (\w+)\) '
    r'\(at ([\d.-]+) ([\d.-]+) (\d+)\)\s*\n'
    r'\s*\(effects \(font \(size ([\d.]+) ([\d.]+)\)\) \(justify \w+\)\)',
)


def sexp_block(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("bloc non termine")


def square_mcu(text):
    """Remplace le symbole MCU par sa version carree et suit les etiquettes.

    La connectivite de ces schemas passe par des etiquettes globales posees
    exactement sur le point de connexion de chaque broche. Changer la
    geometrie du symbole sans deplacer les etiquettes les detacherait toutes
    en silence : l'ERC ne dirait rien, et le netlist serait vide.
    """
    lib_text = MCU_LIB.read_text(encoding="utf-8")
    squares = {
        m.group(1): sexp_block(lib_text, m.start())
        for m in re.finditer(r'^\s{0,2}\(symbol "([^"]+)"', lib_text, re.M)
    }

    m = re.search(r'\(symbol "%s:([^"]+)"' % MCU_NICK, text)
    if not m:
        raise SystemExit("symbole MCU introuvable dans le schema")
    mcu = m.group(1)
    old_block = sexp_block(text, m.start())

    # Position de l'instance, pour passer des coordonnees symbole a la feuille.
    inst = re.search(
        r'\(symbol \(lib_id "%s:%s"\) \(at ([\d.-]+) ([\d.-]+) \d+\)'
        % (MCU_NICK, mcu), text
    )
    if not inst:
        raise SystemExit("instance du MCU introuvable")
    ux, uy = float(inst.group(1)), float(inst.group(2))

    old_pins = {n: (x, y, a) for n, _nm, x, y, a in pg.parse_pins(old_block)}
    new_pins = {n: (x, y, a) for n, _nm, x, y, a in pg.parse_pins(squares[mcu])}
    if set(old_pins) != set(new_pins):
        raise SystemExit("les deux symboles n'ont pas les memes broches")

    move = {}
    for num, (ox, oy, _oa) in old_pins.items():
        nx, ny, na = new_pins[num]
        move[(round(ux + ox, 2), round(uy - oy, 2))] = (
            round(ux + nx, 2), round(uy - ny, 2), na
        )

    moved = [0]

    def relabel(m):
        key = (round(float(m.group(3)), 2), round(float(m.group(4)), 2))
        if key not in move:
            return m.group(0)
        moved[0] += 1
        x, y, ang = move[key]
        rot, just = LABEL_DIR[ang]
        return (
            '(global_label "%s" (shape %s) (at %s %s %d)\n'
            '    (effects (font (size %s %s)) (justify %s))'
            % (m.group(1), m.group(2), _fmt(x), _fmt(y), rot,
               m.group(6), m.group(7), just)
        )

    text = LABEL_RE.sub(relabel, text)
    if moved[0] != len(move):
        raise SystemExit(
            "%d etiquettes deplacees sur %d broches — le schema serait casse"
            % (moved[0], len(move))
        )
    text = text.replace(
        old_block, squares[mcu].replace('(symbol "%s"' % mcu,
                                        '(symbol "%s:%s"' % (MCU_NICK, mcu), 1)
    )
    return text, mcu, len(move), moved[0]


def _fmt(v):
    return ("%.2f" % v).rstrip("0").rstrip(".") or "0"


def install_sch(name, src):
    text = src.read_text(encoding="utf-8")
    text = re.sub(r'\(project "[^"]*"', '(project "%s"' % name, text)
    text, mcu, npins, nlab = square_mcu(text)
    print("  %s : symbole carre, %d broches, %d etiquettes suivies"
          % (mcu, npins, nlab))
    return text


def update_lib_table(out):
    table = out / "sym-lib-table"
    text = (
        table.read_text(encoding="utf-8")
        if table.exists()
        else "(sym_lib_table\n  (version 7)\n)\n"
    )
    added = []
    for nick, path in LIBS.items():
        entry = (
            '  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s")(options "")'
            '(descr "Devkit C2000"))' % (nick, path.as_posix())
        )
        if entry in text:
            continue
        # L'entree existe peut-etre avec une autre uri : la remplacer plutot
        # que d'en ajouter une seconde sous le meme nickname.
        old = re.search(r'^ *\(lib \(name "%s"\).*$' % re.escape(nick),
                        text, re.M)
        if old:
            text = text[: old.start()] + entry + text[old.end():]
        else:
            text = text.rstrip().rstrip(")").rstrip() + "\n" + entry + "\n)\n"
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
            pro = pg.gen_pro(name)
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
