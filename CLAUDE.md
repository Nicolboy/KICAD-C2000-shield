# Projet PCB — KiCad 10, Windows

cle github: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE4f3+cYDYeS9AhdrAqW053Hjwf6gioSQ3DBR904tEx9 contact@nicolasboyer.fr (github dans le dossier.ssh)

## Environnement
- KiCad 10 doit être OUVERT avec le projet chargé. L'API IPC ne marche
  pas en headless sur cette version.
- venv: .venv\Scripts\python.exe — kicad-python (kipy) installé.
- kicad-cli est dans le PATH.
-https://github.com/Nicolboy/testkicad et main

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
| Générateurs | `gen_symbole_mcu.py`, `gen_shield.py`, `gen_devkit.py` |
| Projets KiCad | `shield.*`, `devkit_A_F280037.*`, `devkit_B_F28P551.*` — **trois, pas un de plus** |
| Librairies | `lib/` versionné, `build/` généré |
| Documents | `doc/` — brochages, spécification, README des librairies |
| Boîte de réception | `imports/` — **ignoré par git**, rien ne doit en dépendre à l'ouverture |

## Vérification avant tout commit

Sur les trois projets : `shield`, `devkit_A_F280037`, `devkit_B_F28P551`.

```
kicad-cli sch erc --exit-code-violations <projet>.kicad_sch
kicad-cli pcb drc --exit-code-violations <projet>.kicad_pcb
```

## Décisions de conception à ne pas défaire

Ces choix ont l'air d'inefficacités et n'en sont pas. Ne pas les « optimiser »
sans décision explicite de ma part.

1. **PWM3 et PWM4 (B10 à B13) restent en réserve, et restent des PWM.** Ce sont
   deux paires HRPWM complémentaires avec temps mort matériel, câblées de bout
   en bout sur la nappe PWM alors que rien ne s'en sert encore. Ne pas les
   réaffecter à une commande lente sous prétexte qu'elles sont libres : on
   perdrait les deux seules paires complémentaires disponibles, et la nappe PWM
   est la seule à alternance stricte pensée pour des fronts rapides. Les
   commandes lentes du shield — Stage1_EN, Stage2_EN, HV_EN, Discharge — ont
   leur propre nappe GPIO.
2. **Alternance signal / masse stricte 1:1 sur les quatre nappes.** Non
   négociable, c'est de la mesure de courant. Seule exception, voulue :
   `VREF_ADC` et `VREFLO_SENSE` sont adjacents en A23/A24 et en positions 6/7
   de la nappe ADC-2. C'est une paire de référence, pas deux signaux — les
   séparer par une masse rendrait la mesure différentielle fausse au lieu de la
   protéger.
3. **Les 16 voies ADC du boîtier sortent toutes, pour 9 nécessaires.** Les cinq
   libres — A11, A12, A14, A15, A16 — sont câblées jusqu'aux cinq réserves de
   la nappe ADC-2, dans le même ordre. Une voie ajoutée plus tard se raccorde
   sans retoucher une seule carte. Ne pas « récupérer » ces positions.
4. **Chaque shunt sort deux fois : `_MES` filtré et `_CMP` direct.** Ça a l'air
   d'un doublon et n'en est pas. Le chemin `_CMP` attaque le CMPSS sans filtre
   anti-repliement, donc sans retard sur le déclenchement de la Trip Zone, et
   un défaut sur le filtre ne désarme pas la protection. Ne jamais fusionner
   les deux chemins ni insérer un filtre sur `_CMP` (Rs ≤ 50 Ω).
5. **nRESET en drain ouvert uniquement.** Le MCU tire lui-même la ligne à zéro
   sur watchdog et brownout. Jamais de sortie push-pull côté shield.
6. **Point de jonction VSS/VSSA unique**, près du boîtier, une seule masse au
   connecteur.
7. **GND et +5V restent en `power_in`, avec un PWR_FLAG par net.** Le
   connecteur alimente bien la carte, mais le brochage les décrit en entrée et
   c'est lui qui fait autorité. Un net qui n'a que des `power_in` fait lever
   `power_pin_not_driven` à l'ERC, même avec un symbole de masse dessus : le
   PWR_FLAG répond à ça sans toucher au type électrique des broches. Ne pas
   les passer en `power_out` pour supprimer les flags.

## Deux variantes de PCB

F280037 et F28P551 partagent le connecteur **à 100 %, 56 positions sur 56**.
C'est un arbitrage, pas une coïncidence : les LED sont posées sur les E/S non
communes aux deux boîtiers, précisément pour que le connecteur reste identique.

Les quatre divergences sont toutes locales à la carte devkit, aucune ne
traverse le connecteur :

| Broche | PCB A — F280037 | PCB B — F28P551 |
|---|---|---|
| 27 | VDD 1,2 V, découplage | LED bleue (GPIO20) |
| 28 | VDDIO 3,3 V | LED rouge (GPIO21) |
| 40 | LED rouge (GPIO32) | pastille de test |
| 46 | LED bleue (GPIO39) | VREGENZ à VSS |

Le fond de l'affaire est le régulateur 1,2 V : le F28P551 a le sien en interne,
activé par VREGENZ à VSS ; le F280037 en 64 PM non-Q n'a pas cette broche et
demande un LDO de plus. Toute divergence hors de cette liste est une erreur.

## Points ouverts — ne pas inventer de valeur

- Broches de mode de démarrage des deux MCU : à lire dans le manuel technique.
- VREFHI en mode externe : plage, impédance de source, courant.
- Courant de sortie GPIO : le mode 20 mA du F28P551 n'est pas confirmé dans
  SPRSPC5. Considérer 4 mA. Les DPC817 à 5 mA imposent un buffer côté shield.
- État au reset de GPIO39 (LED, PCB F280037).

Si une de ces valeurs est nécessaire, demander — ne pas combler par une
estimation plausible.
