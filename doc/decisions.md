# Décisions de conception

Ce document rassemble les choix qui ont l'air d'inefficacités et n'en sont pas.
Chacun a coûté quelque chose — une broche, une piste, un composant — en échange
d'une propriété qu'on ne voulait pas perdre.

Il existe parce que ces choix sont exactement ceux qu'on « optimise » six mois
plus tard, faute de se rappeler ce qu'ils protégeaient. Chaque entrée dit donc
trois choses : la décision, sa raison, et ce qui casse si on la défait.

Ce fichier fait autorité sur les décisions. Le brochage, lui, est décrit dans
[`spec-devkit.md`](spec-devkit.md), les nappes dans
[`nappes-shield.md`](nappes-shield.md).

---

## 1. Le connecteur est identique sur les deux MCU, et ça se paie

**Décision.** Les deux devkits, F280037 et F28P551, exposent le même connecteur
— 56 positions sur 56. Pour y parvenir, les LED sont posées sur les
entrées/sorties **non communes** aux deux boîtiers.

**Pourquoi.** Poser une LED est le besoin le plus trivial de la carte ; c'est
donc lui qu'on sacrifie. En le reléguant sur les broches qui divergent, on
libère toutes les broches communes pour ce qui traverse le connecteur. Le shield
devient indifférent au MCU monté dessus.

**Ce qui casse.** Déplacer une LED sur une broche commune la retire du domaine
partagé et rompt l'interchangeabilité. Il faudrait alors deux shields.

Les quatre divergences, toutes locales à la carte devkit :

| Broche | F280037 | F28P551 |
|---|---|---|
| 27 | VDD 1,2 V, découplage | LED bleue (GPIO20) |
| 28 | VDDIO 3,3 V | LED rouge (GPIO21) |
| 40 | LED rouge (GPIO32) | pastille de test |
| 46 | LED bleue (GPIO39) | VREGENZ à VSS |

La cause profonde est le régulateur 1,2 V : le F28P551 a le sien en interne,
activé par VREGENZ à VSS ; le F280037 en 64 PM non-Q n'a pas cette broche et
demande un LDO supplémentaire. **Toute divergence hors de cette liste est une
erreur.**

---

## 2. PWM3 et PWM4 restent en réserve, et restent des PWM

**Décision.** Les positions B10 à B13 portent `PWM3_A/B` et `PWM4_A/B`, câblées
de bout en bout sur la nappe PWM alors que rien ne s'en sert encore.

**Pourquoi.** Ce sont les deux seules paires complémentaires HRPWM avec temps
mort matériel encore disponibles. La nappe PWM est aussi la seule à alternance
signal/masse pensée pour des fronts rapides — un PWM posé ailleurs n'aurait pas
le même environnement.

**Ce qui casse.** Les réaffecter à une commande lente sous prétexte qu'elles
sont libres consomme une ressource rare pour un besoin que n'importe quel GPIO
satisfait. Les commandes lentes du shield — `Stage1_EN`, `Stage2_EN`, `HV_EN`,
`Discharge` — ont leur propre nappe GPIO, faite pour elles.

---

## 3. Alternance signal / masse stricte 1:1 sur les quatre nappes

**Décision.** Un conducteur sur deux est une masse, sur les quatre nappes. Aucune
ligne d'alimentation ne circule dedans.

**Pourquoi.** C'est de la mesure de courant. Le retour de chaque signal longe le
signal lui-même, la boucle reste petite, la diaphonie s'effondre.

**Ce qui casse.** Récupérer une masse pour y passer un signal de plus donne un
conducteur gratuit et une mesure qui dérive sans qu'on sache pourquoi.

**Exception, voulue.** `VREF_ADC` et `VREFLO_SENSE` sont **adjacents** — A27/A28
au connecteur, positions 6 et 7 de la nappe ADC-2. C'est une paire de référence,
pas deux signaux indépendants : la conversion est ramenée à
(VIN − VREFLO) / (VREFHI − VREFLO). Les séparer par une masse rendrait la mesure
différentielle fausse au lieu de la protéger.

C'est aussi la raison pour laquelle le **+5 V a son propre connecteur**. Les
500 mA de la commande n'ont pas à partager leur retour avec les masses de
référence des voies ADC : c'était précisément le mécanisme d'erreur à éviter.

---

## 4. Chaque shunt sort deux fois : `_MES` filtré, `_CMP` direct

**Décision.** La sortie de chaque AMC0300R est reprise deux fois sur le shield.
Un chemin filtré vers la voie de mesure, un chemin direct vers le comparateur.

**Pourquoi.** Le chemin `_CMP` attaque le CMPSS sans filtre anti-repliement : la
Trip Zone se déclenche sans le retard qu'introduirait le filtre. Et les deux
chemins étant indépendants, un défaut sur le filtre ne désarme pas la
protection.

**Ce qui casse.** Fusionner les deux chemins, ou insérer un filtre sur `_CMP`,
remet le retard dans la boucle de protection et recrée le point de défaillance
unique. Contrainte à respecter : Rs ≤ 50 Ω sur le chemin comparateur.

| Voie | Broche | CMPSS | Rôle |
|---|---|---|---|
| `I_SHUNT1_CMP` | 9 | CMP1_HP0 | seuil DAC interne → Trip Zone, sans filtre |
| `I_SHUNT1_MES` | 13 | — | mesure ADC, filtrée |
| `I_SHUNT2_CMP` | 25 | CMP2_HP3 | chemin direct |
| `I_SHUNT2_MES` | 24 | — | mesure ADC, filtrée |

---

## 5. Les 16 voies ADC sortent toutes, pour 9 nécessaires

**Décision.** Toutes les voies ADC du boîtier sont exportées. Les cinq libres —
A12, A14, A15, A17, A18 — sont câblées jusqu'aux cinq réserves de la nappe
ADC-2, dans le même ordre.

**Pourquoi.** Une voie de mesure ajoutée plus tard se raccorde de bout en bout
sans retoucher une seule carte. La marge est volontaire et son coût est nul :
ces broches ne servaient à rien d'autre.

**Ce qui casse.** « Récupérer » ces positions pour autre chose économise cinq
pistes et transforme le moindre ajout de mesure en nouvelle révision des trois
cartes.

---

## 6. nRESET en drain ouvert uniquement

**Décision.** La ligne `nRESET` (B3) n'est jamais attaquée en push-pull depuis
le shield.

**Pourquoi.** Le MCU tire lui-même cette ligne à zéro sur watchdog et sur
brownout. C'est une ligne à plusieurs maîtres.

**Ce qui casse.** Une sortie push-pull côté shield met en conflit deux étages
lorsque le MCU se réinitialise — courant de court-circuit, et un reset qui
n'aboutit pas.

---

## 7. Point de jonction VSS/VSSA unique

**Décision.** Les masses numérique et analogique se rejoignent en **un seul
point**, près du boîtier, et une seule masse remonte au connecteur.

**Pourquoi.** Deux jonctions créent une boucle, et la boucle capte.

---

## 8. `GND` et `+5V` en `power_in`, avec un `PWR_FLAG` par net

**Décision.** Les broches d'alimentation du connecteur gardent le type
électrique `power_in`, et chaque net porte un `PWR_FLAG`.

**Pourquoi.** Le connecteur alimente bien la carte, mais c'est le brochage qui
fait autorité et il les décrit en entrée. Un net composé uniquement de
`power_in` fait lever `power_pin_not_driven` à l'ERC, même avec un symbole de
masse dessus : le `PWR_FLAG` répond à ça sans toucher au type électrique.

**Ce qui casse.** Passer les broches en `power_out` fait taire l'ERC en mentant
sur la nature du connecteur. C'est la documentation qu'on dégrade pour obtenir
un rapport propre.

---

## 9. Le shield s'édite à la main, les devkits se régénèrent

**Décision.** Les trois schémas n'ont pas le même statut, et il faut le savoir
avant d'ouvrir KiCad :

| Schéma | Édition |
|---|---|
| `devkit_A_F280037.kicad_sch` | **jetable** — reconstruit par `gen_devkit.py` |
| `devkit_B_F28P551.kicad_sch` | **jetable** — idem |
| `shield.kicad_sch` | **édité à la main**, c'est le fichier de travail |

**Pourquoi.** Le générateur du shield amenait à la ligne de départ — connecteurs
posés, alimentations câblées, un `PWR_FLAG` par net — puis s'arrêtait : le
routage des signaux demande des choix de conception qui n'appartiennent pas à un
script. Ce travail commence maintenant, et il se fait dans KiCad.

`gen_shield.py` a donc été **retiré du dépôt**. Il écrivait `shield.kicad_sch`
en entier et l'aurait écrasé au premier `--force`, sans avertissement. Un
amorçage à usage unique qui traîne dans l'arborescence est un piège, pas un
outil. Il reste dans l'historique git (commit `31ecd50`) si l'on veut repartir
d'une feuille blanche.

**Ce qui casse.** Retoucher un schéma de devkit à la main : la modification
disparaît au prochain `gen_devkit.py --force`. Ce qui doit survivre se modifie
dans `src/` ou dans le générateur.

---

## 10. Les schémas source des devkits sont versionnés dans `src/`

**Décision.** `src/devkit_c2000_A_F280037.kicad_sch` et son homologue B sont
suivis par git. `imports/` reste la boîte de réception, ignorée.

**Pourquoi.** `gen_devkit.py` ne fabrique pas ces schémas : il les recopie et
les retouche — nom de projet, symbole MCU carré, recalage sur la grille de
1,27 mm. La vraie source, c'était donc un dossier non versionné. Un dépôt dont
l'argument est que tout se régénère depuis une source ne peut pas laisser cette
source hors de lui-même.

**Ce qui casse.** Remettre `PROJECTS` sur `imports/` : le jour où ce dossier
disparaît, les deux devkits ne sont plus régénérables et rien ne le signale
avant qu'on essaie.

---

## 11. Deux rangées égales de 28, et une clé mécanique obligatoire

**Décision.** Le connecteur fait 28 + 28, pas 24 + 32. Quatre signaux ont été
retirés pour que les deux rangées tiennent : `CMP_OUT2`, `CLB_OUT2`, `GPIO_2` et
`GPIO_3`. Les broches MCU correspondantes — 62, 54, 53 et 55 — deviennent des
pastilles de test. `CMP_OUT1` et `CLB_OUT1` perdent leur indice.

**Pourquoi.** Deux rangées identiques, c'est un seul type de support, une seule
référence à approvisionner, et un dessin de carte symétrique.

**Ce qui casse — et c'est le point à ne pas oublier.** L'asymétrie 24/32
assurait le détrompage toute seule : une rangée de 24 n'entre pas dans un
support de 32. Ce n'est plus le cas. **Il faut une clé mécanique explicite** —
position obturée aux extrémités, ou ergot sur le support. Sans elle, une carte
branchée à l'envers met le +5 V de B2 sur une entrée analogique.

C'est la contrainte la plus facile à oublier et la plus coûteuse à découvrir
après fabrication.

**Trace.** Le basculement date du 2026-08-30, vers 15 h 25. `doc/spec-devkit.md`
a été recalé depuis `lib/C2000_Devkit_Connectors.kicad_sym` — qui faisait
seule autorité pendant l'intervalle — et vérifié position par position, 56 sur
56.

---

## Points ouverts — ne pas combler par une estimation

Ces valeurs manquent. Elles demandent une lecture de datasheet ou une mesure,
pas une approximation plausible.

- Broches de mode de démarrage des deux MCU : à lire dans le manuel technique.
- `VREFHI` en mode externe : plage, impédance de source, courant. Et le choix
  2,5 V ou 3,0 V, selon la pleine échelle des AMC.
- Courant de sortie GPIO : le mode 20 mA du F28P551 n'est pas confirmé dans
  SPRSPC5. Considérer 4 mA — les DPC817 à 5 mA imposeraient alors un buffer
  côté shield.
- État au reset de GPIO39 (LED, PCB F280037).
- Caractéristiques de sortie des AMC0311S et AMC0300R : impédance, pleine
  échelle, bande passante — pour dimensionner les filtres sous Rs ≤ 50 Ω.
- Courant d'entrée du REFIN des AMC0300R, pour le suiveur.
- Nombre de banques Flash des deux MCU, pour le FOTA.
- Débit SCI maximal accepté par l'autobaud du bootloader : il fixe la durée
  d'indisponibilité pendant une mise à jour.
- Matériel LFU dédié sur le F28P551 : documenté pour le F28003x, à confirmer.
- **Nombre de couches du devkit.** `spec-devkit.md` recommande quatre couches
  pour un plan de masse continu sous la zone analogique ; la contrainte de
  fabrication du `CLAUDE.md` est de deux, en fabrication maison. Les deux ne
  tiennent pas ensemble — arbitrage à faire, ce n'est pas un détail de confort
  sur une chaîne de mesure de courant.
