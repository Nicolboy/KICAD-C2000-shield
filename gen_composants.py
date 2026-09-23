#!/usr/bin/env python3
"""Pose les composants discrets des devkits dans un schema existant.

La connectivite de ces schemas passe entierement par des etiquettes globales
posees sur le point de connexion de chaque broche — pas un seul fil. Ce script
suit la meme convention : pour chaque composant ajoute, il pose le symbole et
une etiquette par broche, au nom du net.

Consequence utile : aucun routage de schema a faire, et l'ordre de pose n'a
aucune importance.

    python gen_composants.py devkit_B_F28P551.kicad_sch

Idempotent : un composant dont la reference existe deja n'est pas repose.
"""

import argparse
import re
import uuid
from pathlib import Path

from kicad_gen import refuser_si_kicad_ouvert


KILIB = Path(r"C:/Program Files/KiCad/10.0/share/kicad/symbols")

# --------------------------------------------------------------------------
# Nomenclature. Chaque entree : (reference, symbole, valeur, empreinte,
# {numero_de_broche: nom_de_net}).
#
# Les valeurs de net sont les etiquettes globales deja presentes dans les
# schemas : VDDIO, VDDA, VDD_CORE, GND, +5V, LED_B, LED_R, BOOT_SEL,
# TP_GPIO32, VREF_ADC, VREFLO_SENSE, JTAG_TMS, ~{nRESET}.
# --------------------------------------------------------------------------

R = "Device:R"
C = "Device:C"
FP_R = "Resistor_SMD:R_0805_2012Metric"
FP_C = "Capacitor_SMD:C_0805_2012Metric"

BOM = [
    # --- regulation -------------------------------------------------------
    # Brochage du symbole : 1 = GND, 2 = VO, 3 = VI. Verifie dans la
    # librairie, pas suppose — les deux variantes SOT-23 du MCP1700 n'ont pas
    # le meme ordre.
    ("U2", "Regulator_Linear:MCP1700x-330xxTT", "MCP1700-3302E/TT",
     "Package_TO_SOT_SMD:SOT-23", {"1": "GND", "2": "VDDIO", "3": "+5V"}),
    ("U3", "Regulator_Linear:MCP1700x-330xxTT", "MCP1700-3302E/TT",
     "Package_TO_SOT_SMD:SOT-23", {"1": "GND", "2": "VDDA", "3": "+5V"}),
    ("C1", C, "10u", FP_C, {"1": "+5V", "2": "GND"}),
    ("C2", C, "10u", FP_C, {"1": "VDDIO", "2": "GND"}),
    ("C3", C, "10u", FP_C, {"1": "+5V", "2": "GND"}),
    ("C4", C, "10u", FP_C, {"1": "VDDA", "2": "GND"}),

    # --- decouplage, spec-devkit.md section 3 -----------------------------
    # VDDIO : 100 nF par broche (43 et 60 ; la broche 28 du PCB A est traitee
    # a part car elle porte une LED sur le PCB B).
    ("C5", C, "100n", FP_C, {"1": "VDDIO", "2": "GND"}),
    ("C6", C, "100n", FP_C, {"1": "VDDIO", "2": "GND"}),
    # VDDA : 2,2 uF + 100 nF, faible bruit prioritaire.
    ("C7", C, "2u2", FP_C, {"1": "VDDA", "2": "GND"}),
    ("C8", C, "100n", FP_C, {"1": "VDDA", "2": "GND"}),
    # VDD 1,2 V : sortie du regulateur interne, a decoupler seulement.
    # Broches 4, 44, 59 reliees entre elles, ~10 uF au total.
    ("C9", C, "100n", FP_C, {"1": "VDD_CORE", "2": "GND"}),
    ("C10", C, "100n", FP_C, {"1": "VDD_CORE", "2": "GND"}),
    ("C11", C, "100n", FP_C, {"1": "VDD_CORE", "2": "GND"}),
    ("C12", C, "10u", FP_C, {"1": "VDD_CORE", "2": "GND"}),
    # Reference ADC : le condensateur se pose entre VREFHI et VREFLO, pas a
    # la masse — c'est une paire differentielle (decisions.md section 3).
    ("C13", C, "2u2", FP_C, {"1": "VREF_ADC", "2": "VREFLO_SENSE"}),

    # --- reset ------------------------------------------------------------
    # XRSn : rappel 2,2 a 10 kohms vers VDDIO, condensateur <= 100 nF vers VSS.
    ("R2", R, "10k", FP_R, {"1": "~{nRESET}", "2": "VDDIO"}),
    ("C14", C, "100n", FP_C, {"1": "~{nRESET}", "2": "GND"}),
    # Cavalier de reset, en remplacement du bouton-poussoir.
    ("J4", "Connector_Generic:Conn_01x02", "RESET",
     "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     {"1": "~{nRESET}", "2": "GND"}),

    # --- JTAG -------------------------------------------------------------
    # Ce composant n'a pas de broche TRSTn (SPRSPC5 section 5.3). Le rappel
    # sur TMS en tient lieu : c'est lui qui maintient le JTAG en reset en
    # fonctionnement normal.
    ("R1", R, "2k2", FP_R, {"1": "JTAG_TMS", "2": "VDDIO"}),

    # --- selection du mode de boot ----------------------------------------
    # SPRSPC5 table 7-8 : Flash demande GPIO24 = 1 ET GPIO32 = 1. Et la
    # section 5.5 precise que les rappels internes des GPIO sont desactives
    # pendant le boot. Sans ces deux resistances le mode de demarrage est
    # indetermine, Parallel IO compris. Pas de cavalier : Flash seul suffit,
    # le chargement en RAM passe par le JTAG.
    ("R3", R, "10k", FP_R, {"1": "BOOT_SEL", "2": "VDDIO"}),
    ("R4", R, "10k", FP_R, {"1": "TP_GPIO32", "2": "VDDIO"}),

    # --- signalisation ----------------------------------------------------
    # LED 3 mm bicolore a cathode commune. Une seule resistance sur la
    # cathode : les deux couleurs partagent donc leur courant, et l'eclat
    # baisse quand les deux sont allumees. Compromis assume pour un temoin.
    ("D1", "Device:LED_Dual_AKA", "LED_BICOLORE_3MM",
     "LED_THT:LED_D3.0mm-3", {"1": "LED_B", "2": "LED_K", "3": "LED_R"}),
    ("R5", R, "1k", FP_R, {"1": "LED_K", "2": "GND"}),
]

# Zone libre de la feuille A2, sous les connecteurs et le MCU. Les coordonnees
# doivent etre des multiples de 1,27 mm : sinon chaque broche tombe hors grille
# et l'ERC leve un endpoint_off_grid par composant pose.
ORIGIN = (38.10, 241.30)   # 30 et 190 pas de 1,27
STEP_X = 25.4
STEP_Y = 25.4
PER_ROW = 8


def uid():
    return str(uuid.uuid4())


def sexp_block(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("bloc non termine")


def _raw_symbol(text, name):
    m = re.search(r'^\t\(symbol "%s"' % re.escape(name), text, re.M)
    if not m:
        raise SystemExit("symbole introuvable : %s" % name)
    return sexp_block(text, m.start())


def _properties(block):
    """[(nom, texte_du_bloc)] des proprietes de premier niveau du symbole."""
    out = []
    for m in re.finditer(r'\n(\t+)\(property "([^"]+)"', block):
        out.append((m.group(2), sexp_block(block, m.start() + 1)))
    return out


def _replace_properties(block, props):
    """Remplace les proprietes du bloc par celles fournies, nom pour nom."""
    by_name = dict(props)
    out, pos = [], 0
    for m in re.finditer(r'\n(\t+)\(property "([^"]+)"', block):
        start = m.start() + 1
        old = sexp_block(block, start)
        out.append(block[pos:start])
        out.append(by_name.get(m.group(2), old))
        pos = start + len(old)
    out.append(block[pos:])
    return "".join(out)


def lib_symbol(lib_id):
    """Bloc de definition du symbole, prefixe par son nickname.

    Les variantes de la librairie standard sont souvent declarees par
    (extends "PARENT") et ne portent aucune broche : sans resoudre l'heritage,
    on obtiendrait un symbole sans un seul pin et l'erreur ne viendrait
    qu'au moment de poser les etiquettes.
    """
    lib, name = lib_id.split(":")
    text = (KILIB / (lib + ".kicad_sym")).read_text(encoding="utf-8")

    # Remonter la chaine d'heritage jusqu'au symbole qui porte vraiment les
    # broches. On repart alors de CE bloc, entier et bien forme, plutot que
    # de recoller deux morceaux : une greffe de sous-unites produit un
    # s-expression que KiCad refuse de charger, sans rien dire de plus qu'un
    # « echec du chargement ».
    ancestry = [name]
    block = _raw_symbol(text, name)
    own_props = _properties(block)
    m = re.search(r'\(extends "([^"]+)"', block)
    while m:
        parent = m.group(1)
        if parent in ancestry:
            raise SystemExit("heritage circulaire sur %s" % lib_id)
        ancestry.append(parent)
        block = _raw_symbol(text, parent)
        m = re.search(r'\(extends "([^"]+)"', block)

    # Une variante n'herite que de la geometrie : ses propres proprietes
    # (Value, Datasheet, Description...) l'emportent. Sans ce report, le bloc
    # pose dans le schema differe de celui que KiCad calcule a l'ouverture, et
    # l'ERC leve lib_symbol_mismatch sur chaque instance.
    if len(ancestry) > 1 and own_props:
        block = _replace_properties(block, own_props)

    # Renommage au nom demande. Attention au piege : dans un schema, seul le
    # symbole de premier niveau porte le prefixe de librairie. Ses sous-unites
    # gardent le nom NU — "TC2050_1_1", pas "Connector:TC2050_1_1". Les
    # prefixer aussi produit un fichier que KiCad refuse de charger, sans
    # autre diagnostic qu'un « echec du chargement ».
    root = ancestry[-1]
    block = block.replace('(symbol "%s_' % root, '(symbol "%s_' % name)
    block = block.replace('(symbol "%s"' % root, '(symbol "%s"' % lib_id, 1)
    # La valeur affichee doit rester celle de la variante, pas de l'ancetre.
    block = re.sub(r'(\(property "Value" ")[^"]*(")',
                   lambda mm: mm.group(1) + name + mm.group(2), block, count=1)
    return block


PIN_RE = re.compile(
    r'\(pin\s+\S+\s+\S+\s*\n?\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\)'
    r'[\s\S]*?\(number\s*\n?\s*"([^"]+)"',
)


def pin_positions(block):
    """{numero: (dx, dy, angle)} en coordonnees symbole."""
    out = {}
    for m in PIN_RE.finditer(block):
        x, y, ang, num = m.groups()
        out[num] = (float(x), float(y), int(ang))
    return out


# Orientation de l'etiquette selon l'angle du pin : le texte s'eloigne du corps.
LABEL_DIR = {0: (180, "right"), 180: (0, "left"),
             90: (270, "right"), 270: (90, "left")}


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def instance(ref, lib_id, value, footprint, x, y, pins, project, sch_uuid):
    out = [
        '\t(symbol (lib_id "%s") (at %.2f %.2f 0) (unit 1)' % (lib_id, x, y),
        '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)',
        '\t\t(uuid "%s")' % uid(),
        '\t\t(property "Reference" "%s" (at %.2f %.2f 0)'
        ' (effects (font (size 1.27 1.27))))' % (ref, x + 2.54, y - 2.54),
        '\t\t(property "Value" "%s" (at %.2f %.2f 0)'
        ' (effects (font (size 1.27 1.27))))' % (esc(value), x + 2.54, y),
        '\t\t(property "Footprint" "%s" (at %.2f %.2f 0)'
        ' (effects (font (size 1.27 1.27)) (hide yes)))' % (esc(footprint), x, y),
    ]
    for num in sorted(pins, key=lambda n: (len(n), n)):
        out.append('\t\t(pin "%s" (uuid "%s"))' % (num, uid()))
    out += [
        '\t\t(instances',
        '\t\t\t(project "%s"' % project,
        '\t\t\t\t(path "/%s" (reference "%s") (unit 1))' % (sch_uuid, ref),
        '\t\t\t)',
        '\t\t)',
        '\t)',
    ]
    return "\n".join(out)


def label(net, x, y, ang):
    rot, just = LABEL_DIR[ang]
    return (
        '\t(global_label "%s" (shape bidirectional) (at %.2f %.2f %d)\n'
        '\t\t(effects (font (size 1.27 1.27)) (justify %s))\n'
        '\t\t(uuid "%s")\n\t)' % (esc(net), x, y, rot, just, uid())
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("schema", type=Path)
    args = ap.parse_args()
    refuser_si_kicad_ouvert(args.schema)

    text = args.schema.read_text(encoding="utf-8")
    project = args.schema.stem
    m = re.search(r'\(uuid "([^"]+)"\)', text)
    sch_uuid = m.group(1)

    existing = set(re.findall(r'\(property "Reference" "(\w+)"', text))
    todo = [e for e in BOM if e[0] not in existing]
    if not todo:
        print("%s : rien a ajouter" % args.schema.name)
        return

    # 1. Definitions de symboles manquantes, dans (lib_symbols ...).
    defs = []
    for _ref, lib_id, _v, _fp, _p in todo:
        if '(symbol "%s"' % lib_id not in text and lib_id not in defs:
            defs.append(lib_id)
    if defs:
        anchor = text.index("(lib_symbols") + len("(lib_symbols")
        blocks = "\n" + "\n".join(
            "\n".join("  " + ln for ln in lib_symbol(d).splitlines())
            for d in defs
        )
        text = text[:anchor] + blocks + text[anchor:]

    # 2. Instances et etiquettes, en fin de fichier.
    geom = {d: pin_positions(lib_symbol(d)) for d in {e[1] for e in todo}}
    parts = []
    for i, (ref, lib_id, value, fp, nets) in enumerate(todo):
        x = ORIGIN[0] + (i % PER_ROW) * STEP_X
        y = ORIGIN[1] + (i // PER_ROW) * STEP_Y
        parts.append(instance(ref, lib_id, value, fp, x, y,
                              nets, project, sch_uuid))
        for num, net in nets.items():
            if num not in geom[lib_id]:
                raise SystemExit("%s : broche %s absente de %s"
                                 % (ref, num, lib_id))
            dx, dy, ang = geom[lib_id][num]
            parts.append(label(net, x + dx, y - dy, ang))

    close = text.rstrip().rfind(")")
    text = text[:close] + "\n".join(parts) + "\n" + text[close:]
    args.schema.write_text(text, encoding="utf-8")
    print("%s : %d composants poses" % (args.schema.name, len(todo)))
    for ref, _l, v, _fp, nets in todo:
        print("   %-4s %-18s %s" % (ref, v, " ".join(sorted(set(nets.values())))))


if __name__ == "__main__":
    main()
