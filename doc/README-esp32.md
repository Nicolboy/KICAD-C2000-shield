# Bibliothèques KiCad — devkit C2000

Format KiCad 7 / 8 (`version 20231120`). Syntaxe et unicité des numéros de
broche vérifiées.

## Contenu

| Fichier | Symboles |
|---|---|
| `C2000_MCU.kicad_sym` | `TMS320F280037CSPM`, `TMS320F28P551SG5PM` |
| `C2000_Devkit_Connectors.kicad_sym` | `DEVKIT_C2000_ROW_A`, `DEVKIT_C2000_ROW_B`, `NAPPE_ADC1`, `NAPPE_ADC2`, `NAPPE_PWM`, `NAPPE_GPIO`, `ALIM_5V` |
| `brochage_connecteur_devkit.csv` | correspondance position ↔ broche MCU ↔ fonction ↔ mux |

## Installation

Préférences → Gérer les bibliothèques de symboles → Ajouter, puis pointer les
deux `.kicad_sym`. Choisir l'onglet **Projet** plutôt que Global si les cartes
sont dans un dépôt versionné.

## Symboles MCU

Les 64 broches, disposées par fonction et non par quadrant du boîtier :

- **gauche** — les 16 entrées ADC, nommées par leurs canaux réels
  (`A2/B6/C9`), suivies de la fonction projet quand elle est attribuée
  (`.../I_SHUNT1_CMP`) ;
- **droite** — les GPIO, nommés `GPIOxx/FONCTION` ;
- **haut** — alimentations et références ;
- **bas** — JTAG, XRSn, VREGENZ.

Empreinte préremplie : `Package_QFP:LQFP-64_10x10mm_P0.5mm`, présente dans les
bibliothèques standard KiCad.

Types électriques posés pour que l'ERC soit utile :

| Broche | Type | Raison |
|---|---|---|
| VDD | `power_out` | sortie du régulateur interne 1,2 V, à découpler seulement |
| VDDIO, VDDA, VSS, VSSA | `power_in` | alimentées de l'extérieur |
| VREFHI, VREFLO | `input` | références, jamais pilotées par la carte |
| ADC | `input` | |
| GPIO | `bidirectional` | |

L'ERC signalera VDD en `power_out` non alimenté par un `power_in` : c'est
attendu. Poser un drapeau *PWR_FLAG* dessus, ou laisser l'avertissement — il
rappelle que cette broche n'est pas une entrée d'alimentation.

## Symboles connecteurs

Les noms de broche portent directement les noms de signaux du brochage
définitif. Les positions de masse s'appellent toutes `GND` et sont en
`power_in` : relier chacune au même net.

`ALIM_5V` est à poser **deux fois**, en parallèle, réunies en un point unique
avant la séparation des deux branches d'alimentation du shield.

## Ce qu'il reste à faire à la main

- Les empreintes de nappe supposent des embases IDC verticales 2×8 au pas
  2,54 mm. Adapter si vous partez sur du 1,27 mm ou du Picoflex.
- `ALIM_5V` pointe sur une empreinte Micro-Fit 1×02 : à changer selon le
  connecteur retenu.
- Les deux PCB devkit partagent les symboles connecteurs mais pas le symbole
  MCU. Les broches 27, 28 et 46 diffèrent : voir le brochage définitif.
- Aucune empreinte personnalisée n'est fournie, toutes viennent des
  bibliothèques standard KiCad.

---

## Schémas générés

`devkit_c2000_A_F280037.kicad_sch` et `devkit_c2000_B_F28P551.kicad_sch`,
format KiCad 8.

Contenu : le MCU, les deux embases du connecteur devkit et l'embase JTAG, avec
**une étiquette globale sur chaque broche**. La connectivité passe entièrement
par les noms de nets — aucun fil, donc aucune jonction manquante possible.
Chaque net du MCU trouve son homologue sur le connecteur.

Ouvrir, puis Outils → Éditer les champs de symboles pour vérifier les
empreintes, et lancer l'ERC.

### Ce qui n'est pas dans le schéma

Volontairement laissé à la main, parce que le placement de ces composants
conditionne les performances et ne se génère pas :

- découplage — 100 nF par broche d'alimentation, 10 µF sur VDD_CORE,
  2,2 µF sur VDDA, **2,2 µF entre VREF_ADC et VREFLO_SENSE** ;
- les deux LDO 3,3 V, sur les nets `VDDIO` et `VDDA` ;
- l'OR-ing d'entrée, deux Schottky depuis VBUS et depuis `+5V` ;
- le connecteur USB ;
- le circuit de reset — poussoir, 10 kΩ vers VDDIO, 100 nF vers GND ;
- le rappel de **2,2 kΩ sur JTAG_TMS vers VDDIO** — il n'y a pas de TRSTn ;
- les deux LED sur `LED_B` et `LED_R`, avec leurs résistances ;
- le cavalier de boot sur `BOOT_SEL` ;
- sur le PCB B, la pastille de test `TP_GPIO32`.

Ces nets apparaissent une seule fois dans le schéma : c'est normal, ils
attendent leur composant. L'ERC les signalera tant que ce n'est pas fait.

### Différences entre les deux schémas

Uniquement le symbole MCU et l'affectation des broches 27, 28, 40 et 46. Les
connecteurs sont strictement identiques.

## Ce qu'il vaut mieux confier à un agent

Le routage, et surtout la conception analogique du shield : dimensionner seize
filtres anti-repliement sous la contrainte Rs ≤ 50 Ω, arbitrer entre RC seul et
suiveur par voie, placer le point de jonction VSS/VSSA. C'est là qu'est la
difficulté restante, et elle demande des itérations.

---

## ESP32-C6-DevKitC-1

`ESP32_C6_Devkit.kicad_sym` : `ESP32_C6_DEVKITC_1_J1`, `ESP32_C6_DEVKITC_1_J3`,
`INTERFACE_HOTE_ESP`. Brochage repris du guide utilisateur v1.2, embases J1 et J3
en 1 × 16.

### Affectation retenue

| Signal | Broche | Remarque |
|---|---|---|
| OLED_SCK | GPIO6 | FSPICLK natif |
| OLED_MOSI | GPIO7 | FSPID natif |
| OLED_CS | GPIO18 | FSPICS2 |
| OLED_DC | GPIO19 | |
| OLED_RST | GPIO20 | |
| TMS_RXD | GPIO10 | sortie ESP vers UART_RX du C2000 |
| TMS_TXD | GPIO11 | entrée ESP depuis UART_TX du C2000 |
| TMS_BOOT_SEL | GPIO2 | 1 = Flash, 0 = boot SCI ROM |
| TMS_nRESET | GPIO3 | **drain ouvert impératif** |

Réserves : GPIO0, GPIO1, GPIO21, GPIO22, GPIO23.
Évitées : GPIO4, GPIO5, GPIO8, GPIO9, GPIO15 (strapping), GPIO12 et GPIO13 (USB
natif), GPIO16 et GPIO17 (console UART).

### Alimentation — point de vigilance

Espressif indique que les trois sources — USB-C natif, USB-C vers UART, et
l'embase 5V — sont **mutuellement exclusives**. Le shield alimentant par J1-14,
il faut soit un cavalier, soit une Schottky en série, pour qu'un branchement USB
pendant la mise au point ne crée pas de conflit.

### Interface hôte

`INTERFACE_HOTE_ESP`, embase 1 × 14 sur le shield : +5V, masses intercalées,
UART vers le C2000, BOOT_SEL, nRESET, et les cinq lignes de l'OLED.

Elle est **indépendante du module ESP32 retenu**. Une petite carte d'adaptation
fait la correspondance vers J1 et J3 du C6-DevKitC-1. Changer d'ESP32 plus tard
ne demande que de refaire cet adaptateur, pas le shield — même raisonnement que
la carte de conditionnement côté C2000.
