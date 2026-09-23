#!/usr/bin/env python3
"""Reporte LED_B et LED_R sur les pastilles GPIO40 (br. 53) et GPIO23 (br. 54).

Pourquoi : GPIO32 doit valoir 1 au boot dans les deux modes utilises — Flash
(1 1) et SCI (0 1). Une LED sur cette broche la tiendrait vers 2,1 V, sous le
VIH de 0,7 x VDDIO, et casserait a la fois le demarrage Flash et la mise a jour
par l'ESP32. GPIO39, l'autre E/S non commune du PCB A, part avec.

Les deux broches d'accueil sont communes aux deux boitiers et sont celles qui
ont le moins de fonctions alternatives a sacrifier : GPIO23 en a 7, GPIO40 en a
9, contre 12 pour GPIO9. Effet de bord souhaitable : les LED deviennent
identiques sur les deux PCB.

    python gen_leds.py devkit_B_F28P551.kicad_sch

Idempotent : les etiquettes deja deplacees ne sont pas retouchees.
"""

import argparse
import re
from pathlib import Path

# Etiquette a poser sur chaque pastille. Les noms TP_* sont ceux qu'ont pris
# les quatre broches retirees du connecteur lors du passage en 2 x 28.
MOVE = {
    "TP_PIN53": "LED_B",   # GPIO40, 9 fonctions alternatives
    "TP_PIN54": "LED_R",   # GPIO23, 7 fonctions — la plus pauvre des quatre
}

# Les anciennes positions deviennent des pastilles de test nues. Elles ne sont
# PAS les memes sur les deux PCB — c'etait tout l'interet de poser les LED sur
# les E/S non communes (decisions.md section 1).
#
#   PCB A : LED bleue GPIO39 br. 46, LED rouge GPIO32 br. 40
#   PCB B : LED bleue GPIO20 br. 27, LED rouge GPIO21 br. 28
FREE_BY_VARIANT = {
    "A": {"LED_B": "TP_PIN46", "LED_R": "TP_PIN40"},
    "B": {"LED_B": "TP_PIN27", "LED_R": "TP_PIN28"},
}


def variant_of(path):
    name = path.stem
    if "F280037" in name:
        return "A"
    if "F28P551" in name:
        return "B"
    raise SystemExit("variante indeterminee pour %s" % name)

LABEL = re.compile(r'(\(global_label\s+")([^"]*)(")')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("schema", type=Path)
    args = ap.parse_args()
    text = args.schema.read_text(encoding="utf-8")
    FREE = FREE_BY_VARIANT[variant_of(args.schema)]

    names = {m[1] for m in LABEL.findall(text)}
    if not (set(MOVE) & names):
        print("%s : pastilles deja reaffectees" % args.schema.name)
        return

    # Deux passes, sinon LED_R poserait sur une etiquette qu'on vient de creer.
    tmp = {old: "\x00%d\x00" % i for i, old in enumerate(MOVE)}
    counts = {}

    def first(m, table):
        old = m.group(2)
        if old in table:
            counts[old] = counts.get(old, 0) + 1
            return m.group(1) + table[old] + m.group(3)
        return m.group(0)

    # LED_R et LED_B quittent leur broche d'origine.
    text = LABEL.sub(lambda m: first(m, FREE), text)
    # Les pastilles 53 et 54 prennent leur place.
    text = LABEL.sub(lambda m: first(m, tmp), text)
    for old, token in tmp.items():
        text = text.replace(token, MOVE[old])

    args.schema.write_text(text, encoding="utf-8")
    print("%s :" % args.schema.name)
    for old, new in FREE.items():
        print("   %-8s libere  -> %-12s (%d etiquette)" %
              (old, new, counts.get(old, 0)))
    for old, new in MOVE.items():
        print("   %-8s devient -> %-12s (%d etiquette)" %
              (old, new, counts.get(old, 0)))


if __name__ == "__main__":
    main()
