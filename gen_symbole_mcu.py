#!/usr/bin/env python3
"""Redessine les symboles MCU en carre, 16 broches par cote, 1 a 64.

Entree : lib/C2000_MCU.kicad_sym, qui fait autorite sur les numeros, les noms
et les types electriques. Ce script ne change que la geometrie.

Disposition, celle du LQFP-64 vu de dessus, numerotation antihoraire :

    64 .. 49   (haut, de droite a gauche)
     1        33
     ..  U1   ..   gauche 1-16 haut en bas, droite 33-48 bas en haut
    16        48
    17 .. 32   (bas, de gauche a droite)

    python gen_symbole_mcu.py [-o build/]
"""

import argparse
import re
from pathlib import Path

SRC = Path("lib/C2000_MCU.kicad_sym")
OUT_NAME = "C2000_MCU_LQFP64.kicad_sym"

PITCH = 2.54
PER_SIDE = 16
PIN_LEN = 5.08

FONT = 1.27          # hauteur de police des noms de broche
CHAR_W = 0.8 * FONT  # avance par caractere de la police batonnet KiCad
NAME_OFF = 0.508     # (pin_names (offset ...)) : retrait du texte vers le corps
MARGE = 1.27         # jeu visuel entre deux textes qui se font face

# 16 broches au pas de 2,54 occupent 38,1 mm, centrees sur l'origine.
SPAN = (PER_SIDE - 1) * PITCH / 2.0        # 19.05

# Le corps est agrandi dans main() d'apres la longueur reelle des noms.
BODY = SPAN + PITCH
PIN_OFF = BODY + PIN_LEN


def dimensionner(names):
    """Fixe BODY pour que les noms des quatre cotes ne se croisent jamais.

    Les noms des broches gauche/droite s'ecrivent horizontalement vers
    l'interieur, sur les lignes y de -SPAN a +SPAN. Ceux du haut/bas
    s'ecrivent verticalement vers l'interieur, sur les colonnes x de -SPAN a
    +SPAN. Les deux familles se recouvrent des que le texte depasse SPAN.

    Il suffit donc que le corps laisse, entre son bord et la bande occupee par
    les broches de la face perpendiculaire, la place d'un nom entier :

        BODY >= SPAN + longueur_du_plus_long_nom + marge

    Arrondi au multiple de 1,27 superieur, pour rester sur la grille.
    """
    global BODY, PIN_OFF
    longest = max((len(n) for n in names), default=0)
    besoin = SPAN + NAME_OFF + longest * CHAR_W + MARGE
    demi = 1.27
    BODY = max(SPAN + PITCH, -(-besoin // demi) * demi)
    PIN_OFF = BODY + PIN_LEN
    return longest

PIN_RE = re.compile(
    r'\(pin\s+(\S+)\s+(\S+)\s+\(at\s+\S+\s+\S+\s+\d+\)\s+\(length\s+\S+\)'
    r'.*?\(name\s+"((?:[^"\\]|\\.)*)"'
    r'.*?\(number\s+"([^"]+)"',
    re.S,
)

PROP_RE = re.compile(r'\(property "(\w+)" "((?:[^"\\]|\\.)*)"')


def blocks(text):
    """{nom: bloc} des symboles de premier niveau."""
    out = {}
    for m in re.finditer(r'^\s{0,2}\(symbol "([^"]+)"', text, re.M):
        s, name, depth = m.start(), m.group(1), 0
        for i in range(s, len(text)):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    out[name] = text[s : i + 1]
                    break
    return out


def place(number):
    """(x, y, angle) de la broche, en coordonnees symbole.

    Le pin est ecrit a son point de connexion, et son angle indique la
    direction dans laquelle il s'etend vers le corps : 0 = vers la droite
    (donc broche a gauche), 90 = vers le haut (broche en bas), 180 = vers la
    gauche (broche a droite), 270 = vers le bas (broche en haut).
    """
    i = (number - 1) % PER_SIDE
    side = (number - 1) // PER_SIDE
    if side == 0:
        return -PIN_OFF, SPAN - i * PITCH, 0
    if side == 1:
        return -SPAN + i * PITCH, -PIN_OFF, 90
    if side == 2:
        return PIN_OFF, -SPAN + i * PITCH, 180
    return SPAN - i * PITCH, PIN_OFF, 270


def rebuild(name, block):
    pins = PIN_RE.findall(block)
    if len(pins) != PER_SIDE * 4:
        raise SystemExit(
            "%s : %d broches, il en faut %d" % (name, len(pins), PER_SIDE * 4)
        )

    props = dict(PROP_RE.findall(block))
    prop_pos = {
        "Reference": (0, BODY + 2.54),
        "Value": (0, BODY + 5.08),
    }
    out = ['  (symbol "%s"' % name,
           '    (pin_names (offset 0.508))',
           '    (exclude_from_sim no) (in_bom yes) (on_board yes)']
    for key in ("Reference", "Value", "Footprint", "Datasheet", "Description"):
        if key not in props:
            continue
        x, y = prop_pos.get(key, (0, 0))
        hide = "" if key in prop_pos else " hide"
        out.append(
            '    (property "%s" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))%s))'
            % (key, props[key], _num(x), _num(y), hide)
        )

    out.append('    (symbol "%s_0_1"' % name)
    out.append(
        '      (rectangle (start %s %s) (end %s %s)'
        % (_num(-BODY), _num(BODY), _num(BODY), _num(-BODY))
    )
    out.append('        (stroke (width 0.254) (type default)) (fill (type background))')
    out.append('      )')
    out.append('    )')

    out.append('    (symbol "%s_1_1"' % name)
    for etype, style, pname, number in sorted(pins, key=lambda p: int(p[3])):
        x, y, ang = place(int(number))
        out.append(
            '      (pin %s %s (at %s %s %d) (length %s)'
            % (etype, style, _num(x), _num(y), ang, _num(PIN_LEN))
        )
        out.append(
            '        (name "%s" (effects (font (size 1.27 1.27))))' % pname
        )
        out.append(
            '        (number "%s" (effects (font (size 1.27 1.27))))' % number
        )
        out.append('      )')
    out.append('    )')
    out.append('  )')
    return "\n".join(out)


def _num(v):
    return ("%.2f" % v).rstrip("0").rstrip(".") or "0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="build")
    args = ap.parse_args()

    text = SRC.read_text(encoding="utf-8")
    syms = blocks(text)
    longest = dimensionner(p[2] for b in syms.values() for p in PIN_RE.findall(b))
    body = "\n".join(rebuild(n, b) for n, b in sorted(syms.items()))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / OUT_NAME
    path.write_text(
        '(kicad_symbol_lib (version 20231120) (generator "gen_symbole_mcu")\n'
        + body
        + "\n)\n",
        encoding="utf-8",
    )
    print("Ecrit : %s (%d symboles)" % (path, len(syms)))
    print(
        "  corps %s x %s mm (nom le plus long : %d caracteres)"
        % (_num(2 * BODY), _num(2 * BODY), longest)
    )
    for n in sorted(syms):
        print("  %s : 64 broches, 16 par cote" % n)


if __name__ == "__main__":
    main()
