#!/usr/bin/env python3
"""Reporte l'empreinte de la librairie sur les instances qui l'ont vide.

Les schemas importes portent bien une propriete Footprint sur chaque symbole,
mais avec une valeur vide. Or c'est l'instance que KiCad lit au moment de
« Mettre a jour le PCB depuis le schema » — pas la librairie. Resultat :

    Erreur: Ne peut ajouter le composant 'U1' (empreinte non assignee).

Ce script va chercher la valeur dans le bloc (lib_symbols) du meme fichier,
qui lui la porte, et la recopie sur l'instance.

    python gen_empreintes.py devkit_B_F28P551.kicad_sch

Idempotent : une instance deja renseignee n'est pas touchee.
"""

import argparse
import re
from pathlib import Path

from gen_composants import sexp_block

LIB_ID = re.compile(r'\(symbol\s*\n?\s*\(lib_id "([^"]+)"')
REF = re.compile(r'\(property "Reference"\s*\n?\s*"([^"]+)"')
FP = re.compile(r'(\(property "Footprint"\s*\n?\s*")([^"]*)(")')
VALUE = re.compile(r'\(property "Value"\s*\n?\s*"[^"]*"[^\n]*\)')


def _from_cache(text):
    """{lib_id: empreinte} lus dans la section (lib_symbols) du schema."""
    out = {}
    block = sexp_block(text, text.index("(lib_symbols"))
    for m in re.finditer(r'\n\s*\(symbol "([^":]+:[^"]+)"', block):
        sym = sexp_block(block, m.start() + 1)
        fp = FP.search(sym)
        if fp and fp.group(2):
            out[m.group(1)] = fp.group(2)
    return out


def _from_libraries(root):
    """{lib_id: empreinte} lus dans les librairies de sym-lib-table.

    Le cache (lib_symbols) du schema n'est pas fiable : sur les fichiers
    importes, plusieurs symboles y ont perdu leur empreinte alors que la
    librairie la porte. C'est donc la librairie qui fait foi.
    """
    out = {}
    table = root / "sym-lib-table"
    if not table.exists():
        return out
    for nick, uri in re.findall(r'\(name "([^"]+)"\).*?\(uri "([^"]+)"\)',
                                table.read_text(encoding="utf-8")):
        path = root / uri.replace("${KIPRJMOD}/", "")
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r'^\s{0,4}\(symbol "([^":]+)"', text, re.M):
            fp = FP.search(sexp_block(text, m.start()))
            if fp and fp.group(2):
                out["%s:%s" % (nick, m.group(1))] = fp.group(2)
    return out


def library_footprints(text, root):
    """Le cache du schema, complete puis surclasse par les librairies."""
    out = _from_cache(text)
    out.update(_from_libraries(root))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("schema", type=Path)
    args = ap.parse_args()
    text = args.schema.read_text(encoding="utf-8")
    known = library_footprints(text, args.schema.resolve().parent)

    fixed, missing = [], []
    # De la fin vers le debut : chaque substitution decale ce qui suit.
    spots = list(LIB_ID.finditer(text))
    for m in reversed(spots):
        blk = sexp_block(text, m.start())
        ref = REF.search(blk)
        if not ref:
            continue
        fp = FP.search(blk)
        if fp and fp.group(2):
            continue                      # deja renseignee
        value = known.get(m.group(1))
        if not value:
            missing.append((ref.group(1), m.group(1)))
            continue
        if fp:
            new = blk[:fp.start(2)] + value + blk[fp.end(2):]
        else:
            # Les deux formats coexistent dans le depot : KiCad 10 ecrit une
            # propriete Footprint vide, KiCad 8 n'en ecrit aucune. Dans le
            # second cas il faut l'inserer, juste apres Value.
            val = VALUE.search(blk)
            if not val:
                missing.append((ref.group(1), m.group(1)))
                continue
            end = val.end()
            pad = "\t\t" if "\n\t\t(property" in blk else "    "
            new = (blk[:end]
                   + '\n%s(property "Footprint" "%s" (at 0 0 0)'
                     ' (effects (font (size 1.27 1.27)) (hide yes)))'
                     % (pad, value)
                   + blk[end:])
        text = text[:m.start()] + new + text[m.start() + len(blk):]
        fixed.append((ref.group(1), value))

    if fixed:
        args.schema.write_text(text, encoding="utf-8")
    print("%s :" % args.schema.name)
    for ref, value in reversed(fixed):
        print("   %-4s -> %s" % (ref, value))
    for ref, lib_id in missing:
        print("   %-4s : AUCUNE empreinte en librairie (%s)" % (ref, lib_id))
    if not fixed and not missing:
        print("   rien a faire")


if __name__ == "__main__":
    main()
