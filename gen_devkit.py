#!/usr/bin/env python3
"""Monte les deux projets KiCad des devkits a partir de src/.

Les schemas viennent tout faits de src/ : ce script ne les fabrique pas, il les
installe a la racine du depot et leur ajoute le .kicad_pro et le .kicad_pcb qui
manquent pour former un projet.

ATTENTION : les .kicad_sch produits a la racine sont jetables. Toute retouche
manuelle y est perdue au prochain --force. Ce qui doit survivre se modifie dans
src/, qui est versionne, ou dans ce script.

Trois retouches sont appliquees a chaque schema installe :

1. le champ (project "...") est reecrit au nom reel du projet — les deux
   fichiers portent "devkit_c2000" alors qu ils donnent deux projets
   distincts ;
2. le symbole MCU est remplace par sa version carree (gen_symbole_mcu.py) ;
3. les quatre symboles sont recales sur la grille de 1,27 mm, faute de quoi
   leurs broches sont hors grille et l'ERC leve endpoint_off_grid.

Les etiquettes globales suivent dans les deux derniers cas : c'est elles qui
portent toute la connectivite.

    python gen_devkit.py [--force]
"""

import argparse
import json
import re
from pathlib import Path

import kicad_gen as pg

# Les schemas source sont versionnes dans src/. imports/ reste la boite de
# reception : on y depose, on copie dans src/, et c'est src/ qui fait foi.
# Sans ca la source de verite des deux devkits ne serait pas dans le depot.
SRC = Path("src")
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
    ("devkit_A_F280037", SRC / "devkit_c2000_A_F280037.kicad_sch"),
    ("devkit_B_F28P551", SRC / "devkit_c2000_B_F28P551.kicad_sch"),
]

# Contour provisoire : chaque rangee fait 28 positions au pas 2,54, soit une
# carte de 71 mm de long (doc/README-lib.md). Dimension a confirmer.
BOARD_W = 90.0
BOARD_H = 45.0


# Position de l'instance du MCU sur la feuille. Les fichiers fournis la
# posent en (127, 100) : 100 n'est pas un multiple de 1,27 mm, donc les 64
# broches tombent hors grille et l'ERC leve endpoint_off_grid. 101,6 = 80 pas.
MCU_AT = (127.0, 101.6)
GRID = 1.27

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


def snap(v):
    """Ramene une coordonnee sur la grille de connexion."""
    return round(round(v / GRID) * GRID, 2)


def retouche(text):
    """Symbole MCU en carre, et toutes les instances recalees sur la grille.

    La connectivite de ces schemas passe par des etiquettes globales posees
    exactement sur le point de connexion de chaque broche, sans un seul fil.
    Deplacer un symbole sans deplacer ses etiquettes les detacherait toutes
    en silence : l'ERC ne dirait rien de plus, et la netlist serait vide.
    Les deux operations partagent donc le meme mecanisme — pour chaque
    broche, ou elle etait, ou elle va — et les etiquettes suivent.
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
    mcu_lib_id = "%s:%s" % (MCU_NICK, mcu)
    old_mcu_block = sexp_block(text, m.start())

    for v in MCU_AT:
        if snap(v) != round(v, 2):
            raise SystemExit(
                "MCU_AT %s n'est pas sur la grille de %s mm" % (MCU_AT, GRID)
            )

    # Geometrie de chaque symbole : celle du schema, sauf pour le MCU dont on
    # veut la version carree.
    # Les definitions ne sont pas toujours en debut de ligne : les fichiers
    # fournis collent la parenthese fermante de la precedente devant. Seules
    # les definitions de premier niveau portent un nom "librairie:symbole",
    # les sous-symboles d'unite n'ont pas de deux-points.
    lib_pins = {}
    for lm in re.finditer(r'\(symbol "([^":]+:[^"]+)"', text):
        name = lm.group(1)
        block = squares[mcu] if name == mcu_lib_id else sexp_block(text, lm.start())
        lib_pins[name] = {
            n: (x, y, a) for n, _nm, x, y, a in pg.parse_pins(block)
        }
    old_mcu_pins = {
        n: (x, y, a) for n, _nm, x, y, a in pg.parse_pins(old_mcu_block)
    }

    move, shifted = {}, []
    for im in re.finditer(
        r'\(symbol \(lib_id "([^"]+)"\) \(at ([\d.-]+) ([\d.-]+) (\d+)\)', text
    ):
        lib_id = im.group(1)
        if lib_id not in lib_pins:
            continue
        ux, uy = float(im.group(2)), float(im.group(3))
        vx, vy = MCU_AT if lib_id == mcu_lib_id else (snap(ux), snap(uy))
        # Les etiquettes sont posees sur la geometrie actuelle ; pour le MCU
        # c'est celle d'avant le passage en carre.
        source = old_mcu_pins if lib_id == mcu_lib_id else lib_pins[lib_id]
        for num, (ox, oy, _oa) in source.items():
            nx, ny, na = lib_pins[lib_id][num]
            move[(round(ux + ox, 2), round(uy - oy, 2))] = (
                round(vx + nx, 2), round(vy - ny, 2), na
            )
        if (vx, vy) != (ux, uy):
            shifted.append((im.start(), vx - ux, vy - uy))

    # De la fin vers le debut : deplacer un bloc change les offsets suivants.
    for start, dx, dy in reversed(shifted):
        block = sexp_block(text, start)
        text = text.replace(
            block,
            re.sub(
                r'\(at ([\d.-]+) ([\d.-]+) (\d+)\)',
                lambda m: '(at %s %s %s)' % (
                    _fmt(float(m.group(1)) + dx),
                    _fmt(float(m.group(2)) + dy),
                    m.group(3),
                ),
                block,
            ),
            1,
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

    total = len(LABEL_RE.findall(text))
    text = LABEL_RE.sub(relabel, text)
    if moved[0] != total:
        raise SystemExit(
            "%d etiquettes sur %d retrouvent une broche — le schema serait"
            " casse" % (moved[0], total)
        )

    text = text.replace(
        old_mcu_block,
        squares[mcu].replace(
            '(symbol "%s"' % mcu, '(symbol "%s"' % mcu_lib_id, 1
        ),
    )
    return text, mcu, moved[0], len(shifted)


def _fmt(v):
    return ("%.2f" % v).rstrip("0").rstrip(".") or "0"


def install_sch(name, src):
    text = src.read_text(encoding="utf-8")
    text = re.sub(r'\(project "[^"]*"', '(project "%s"' % name, text)
    text, mcu, nlab, nmoved = retouche(text)
    print("  %s carre, %d etiquettes suivies, %d symboles recales"
          % (mcu, nlab, nmoved))
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
