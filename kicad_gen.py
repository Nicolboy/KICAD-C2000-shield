#!/usr/bin/env python3
"""Briques communes aux generateurs de projets KiCad du depot.

Ne genere rien tout seul : fournit les primitives s-expression (fils,
symboles d'alimentation, lecture de broches) et les gabarits de .kicad_pcb
et .kicad_pro partages par gen_shield_2x24.py, gen_shield.py et
gen_devkit.py.
"""

import re
import uuid
from pathlib import Path

# Carte format ESP32 devkit, cf. connecteur-2x24.md
BOARD_W = 64.0
BOARD_H = 28.0
BOARD_X = 100.0
BOARD_Y = 80.0

# Contraintes fab (CLAUDE.md) : 2 couches, piste 1 mm, via 2 mm / percage 0,8 mm
TRACK_MIN = 1.0
VIA_DIA = 2.0
VIA_DRILL = 0.8
CLEARANCE = 0.3


def uid():
    return str(uuid.uuid4())


def indent(block, level):
    pad = "\t" * level
    return "\n".join(pad + ln if ln else ln for ln in block.splitlines())


POWER_LIB = Path(
    r"C:\Program Files\KiCad\10.0\share\kicad\symbols\power.kicad_sym"
)

# Les coordonnees peuvent etre en notation scientifique (3.55271e-15 pour un
# zero calcule) : sans l'exposant, le pin concerne passe inapercu.
NUM = r'-?[\d.]+(?:[eE][-+]?\d+)?'

PIN_RE = re.compile(
    r'\(pin\s+\S+\s+\S+\s+\(at\s+(' + NUM + r')\s+(' + NUM + r')\s+(\d+)\)'
    r'.*?\(name\s+"([^"]+)"'
    r'.*?\(number\s+"([^"]+)"',
    re.S,
)

# Longueur du fil qui relie la broche a son symbole d'alimentation.
STUB = 5.08


def parse_pins(block):
    """[(numero, nom, x, y, angle)] en coordonnees symbole."""
    out = []
    for m in PIN_RE.finditer(block):
        x, y, ang, name, num = m.groups()
        # round() ecrase les zeros calcules ; sans ca l'extremite du fil
        # tombe hors grille.
        out.append((num, name, round(float(x), 3), round(float(y), 3), int(ang)))
    return out


def extract_from(path, name):
    """Extrait un bloc symbole d'une librairie, prefixe par sa lib."""
    text = Path(path).read_text(encoding="utf-8")
    start = text.index('(symbol "%s"' % name)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                block = text[start : i + 1]
                return block.replace(
                    '(symbol "%s"' % name, '(symbol "power:%s"' % name, 1
                )
    raise ValueError("bloc symbole %s non termine" % name)


def wire(x0, y0, x1, y1):
    return (
        '\t(wire (pts (xy %.2f %.2f) (xy %.2f %.2f))\n'
        '\t\t(stroke (width 0) (type default)) (uuid "%s")\n\t)'
        % (x0, y0, x1, y1, uid())
    )


def pwr_symbol(name, ref, x, y, rot, sch_uuid, project,
               show_value=True, direction=1):
    """Instance d'un symbole de la librairie power, pin en (x, y)."""
    value = (
        '\t\t(property "Value" "%s" (at %.2f %.2f %d) (effects (font (size 1.27 1.27))))\n'
        % (name, x + direction * 3.81, y, rot)
        if show_value
        else '\t\t(property "Value" "%s" (at %.2f %.2f 0) (hide yes) (effects (font (size 1.27 1.27))))\n'
        % (name, x, y)
    )
    return (
        '\t(symbol\n'
        '\t\t(lib_id "power:%s")\n'
        '\t\t(at %.2f %.2f %d)\n'
        '\t\t(unit 1)\n'
        '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n'
        '\t\t(uuid "%s")\n'
        '\t\t(property "Reference" "%s" (at %.2f %.2f 0) (hide yes) (effects (font (size 1.27 1.27))))\n'
        '%s'
        '\t\t(pin "1" (uuid "%s"))\n'
        '\t\t(instances\n'
        '\t\t\t(project "%s"\n'
        '\t\t\t\t(path "/%s" (reference "%s") (unit 1))\n'
        '\t\t\t)\n'
        '\t\t)\n'
        '\t)'
        % (name, x, y, rot, uid(), ref, x, y - 6.35, value, uid(), project,
           sch_uuid, ref)
    )


def gen_pcb():
    x0, y0 = BOARD_X, BOARD_Y
    x1, y1 = BOARD_X + BOARD_W, BOARD_Y + BOARD_H
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    edges = []
    for i in range(4):
        sx, sy = corners[i]
        ex, ey = corners[(i + 1) % 4]
        edges.append(
            '\t(gr_line (start %.3f %.3f) (end %.3f %.3f)\n'
            '\t\t(stroke (width 0.1) (type default)) (layer "Edge.Cuts") (uuid "%s")\n\t)'
            % (sx, sy, ex, ey, uid())
        )

    return """(kicad_pcb
\t(version 20241229)
\t(generator "kicad_gen")
\t(generator_version "1.0")
\t(general
\t\t(thickness 1.6)
\t\t(legacy_teardrops no)
\t)
\t(paper "A4")
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(2 "B.Cu" signal)
\t\t(9 "F.Adhes" user "F.Adhesive")
\t\t(11 "B.Adhes" user "B.Adhesive")
\t\t(13 "F.Paste" user)
\t\t(15 "B.Paste" user)
\t\t(5 "F.SilkS" user "F.Silkscreen")
\t\t(7 "B.SilkS" user "B.Silkscreen")
\t\t(1 "F.Mask" user)
\t\t(3 "B.Mask" user)
\t\t(17 "Dwgs.User" user "User.Drawings")
\t\t(19 "Cmts.User" user "User.Comments")
\t\t(21 "Eco1.User" user "User.Eco1")
\t\t(23 "Eco2.User" user "User.Eco2")
\t\t(25 "Edge.Cuts" user)
\t\t(27 "Margin" user)
\t\t(31 "F.CrtYd" user "F.Courtyard")
\t\t(29 "B.CrtYd" user "B.Courtyard")
\t\t(35 "F.Fab" user)
\t\t(33 "B.Fab" user)
\t)
\t(setup
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints no)
\t)
\t(net 0 "")
%s
)
""" % ("\n".join(edges))


def gen_pro(name):
    return {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.1,
                    "copper_line_width": TRACK_MIN,
                    "silk_line_width": 0.15,
                    "silk_text_size_h": 1.0,
                    "silk_text_size_v": 1.0,
                },
                "rules": {
                    "min_clearance": CLEARANCE,
                    "min_track_width": TRACK_MIN,
                    "min_through_hole_diameter": VIA_DRILL,
                    "min_via_annular_width": (VIA_DIA - VIA_DRILL) / 2,
                    "min_via_diameter": VIA_DIA,
                },
                "track_widths": [0.0, TRACK_MIN, 1.5, 2.0],
                "via_dimensions": [
                    {"diameter": 0.0, "drill": 0.0},
                    {"diameter": VIA_DIA, "drill": VIA_DRILL},
                ],
            }
        },
        "meta": {"filename": name + ".kicad_pro", "version": 3},
        "net_settings": {
            "classes": [
                {
                    "clearance": CLEARANCE,
                    "name": "Default",
                    "track_width": TRACK_MIN,
                    "via_diameter": VIA_DIA,
                    "via_drill": VIA_DRILL,
                }
            ]
        },
        "sheets": [],
        "text_variables": {},
    }

