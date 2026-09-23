# Projet PCB — KiCad 10, Windows

## Environnement
- KiCad 10 doit être OUVERT avec le projet chargé. L'API IPC ne marche
  pas en headless sur cette version.
- venv: .venv\Scripts\python.exe — kicad-python (kipy) installé.
- kicad-cli est dans le PATH.
- Dépôt : https://github.com/Nicolboy/KICAD-C2000-shield, branche `main`.
  Clé SSH de compte `~/.ssh/github_nicolboy`, sélectionnée par `~/.ssh/config`.
  Ne jamais remettre de `core.sshCommand` dans le dépôt : ça contourne cette
  configuration et fait échouer le push avec « denied to deploy key ».

## Règles
- Committer avant toute modification (git).
- PCB: passer par kipy sur l'instance ouverte. Ne jamais éditer
  le .kicad_pcb à la main pendant que KiCad est ouvert.
- Schéma: éditer les .kicad_sch directement, KiCad FERMÉ, puis relancer.
- Exports et vérifs: kicad-cli uniquement (pas d'export via l'API en v10).
- Après chaque lot de modifs: kicad-cli pcb drc / kicad-cli sch erc,
  et me rapporter les erreurs sans les corriger d'office.

## Contraintes fab
2 couches, pistes 1mm mini, via 2mm et trou de 0,8mm, fabriqué a la maison
(à remplir: nombre de couches, largeurs mini, vias, fabricant)

# Projet — shield d'isolation C2000, connecteur 24 + 32

## Ce qui fait autorité

`doc/brochage-devkit.md` **est** la source de vérité du brochage : rangée A de
24, rangée B de 32, soit 56 positions. Tout le reste en découle par génération.

- Ne jamais éditer `build/*.kicad_sym` à la main. Modifier le `.md`, relancer le
  générateur.
- Si le symbole et le `.md` divergent, le `.md` a raison.
- `doc/brochage-2x24.md` décrit le connecteur 2 × 24 **abandonné** le
  2026-08-30. Conservé pour mémoire, il ne fait plus autorité sur rien.

## Organisation du dépôt

Un préfixe par groupe, le rôle dans le nom.

| Groupe | Fichiers |
|---|---|
| Brique commune | `kicad_gen.py` — primitives s-expression, gabarits `.kicad_pcb` / `.kicad_pro`. Ne génère rien seul. |
| Générateurs | `gen_symbole_mcu.py`, `gen_devkit.py` |
| Projets KiCad | `shield.*`, `devkit_A_F280037.*`, `devkit_B_F28P551.*` — **trois, pas un de plus** |
| Sources | `src/` — schémas source des devkits, **versionnés** |
| Librairies | `lib/` versionné, `build/` généré |
| Documents | `doc/` — brochages, décisions, spécification, README des librairies |
| Boîte de réception | `imports/` — **ignoré par git**, rien ne doit en dépendre à l'ouverture |

## Quel schéma éditer — à lire avant d'ouvrir KiCad

| Schéma | Édition |
|---|---|
| `shield.kicad_sch` | **à la main**, c'est le fichier de travail |
| `devkit_A_F280037.kicad_sch` | **jetable**, écrasé par `gen_devkit.py --force` |
| `devkit_B_F28P551.kicad_sch` | **jetable**, idem |

Une retouche manuelle sur un devkit est perdue à la régénération suivante, sans
avertissement. Ce qui doit survivre se modifie dans `src/` ou dans le
générateur. `gen_shield.py` a été retiré pour cette raison : il écrasait
`shield.kicad_sch`. Détail dans `doc/decisions.md` §9 et §10.

## Vérification avant tout commit

Sur les trois projets : `shield`, `devkit_A_F280037`, `devkit_B_F28P551`.

```
kicad-cli sch erc --exit-code-violations <projet>.kicad_sch
kicad-cli pcb drc --exit-code-violations <projet>.kicad_pcb
```

## Décisions de conception et points ouverts

`doc/decisions.md` **fait autorité**. Huit décisions qui ont l'air
d'inefficacités et n'en sont pas, chacune avec sa raison et ce qui casse si on
la défait — plus les valeurs encore manquantes.

- Les lire avant de toucher au brochage, aux nappes ou aux types électriques.
- Ne jamais en « optimiser » une sans décision explicite de ma part.
- Ne pas recopier ces décisions ici : deux copies divergent, c'est exactement
  ce que ce dépôt cherche à éviter.
- Pour une valeur listée comme ouverte : demander, ne pas estimer.
