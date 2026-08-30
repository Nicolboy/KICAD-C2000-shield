# Devkit TMS320 C2000 — spécification consolidée

Remplace tous les documents de brochage antérieurs. Deux PCB à partir d'un seul
schéma, `DEVKIT_C2000_A` pour le F280037CSPM et `DEVKIT_C2000_B` pour le
F28P551SG5PM.

Les 64 broches sont attribuées et vérifiées sur les deux variantes.

---

## 1. Ce qui a changé depuis les premières versions

| Point | Avant | Maintenant |
|---|---|---|
| Cible | F28027 + deux 64 broches | **F280037 et F28P551 seuls** |
| Connecteur | 2 × 32, symétrique | **rangée A 1×24, rangée B 1×32** |
| Alimentation au connecteur | +3V3, +3V3_A, +5V | **+5V et masses uniquement** |
| Origine du 5 V | USB du devkit | **carte de puissance**, USB en secours |
| I2C | GPIO32 / GPIO33 | **GPIO8 / GPIO10**, mux 9 |
| Reset | bouton seul | **bouton + nRESET en B3** |
| Mode de boot | non résolu | **GPIO24 en B4**, BMSP unique par OTP |
| Voies shunt | une broche chacune | **dédoublées**, mesure + comparateur |
| LED | GPIO24 et GPIO32 | **E/S non communes**, voir §5 |
| VREFLO | non exportée | **exportée**, paire avec VREFHI |
| Isolation, NCM3 | sur le shield | **carte de puissance** |

---

## 2. Attribution des 64 broches

### Rangée A — analogique, 1 × 24

| Broche | Position | Signal | Broche | Position | Signal |
|---|---|---|---|---|---|
| 6 | A2 | Vin | 19 | A14 | ADC_10 |
| 7 | A3 | Vout | 20 | A15 | ADC_11 |
| 8 | A4 | V1 | 23 | A16 | ADC_12 |
| 10 | A6 | Temp1 | 13 | A18 | I_SHUNT1_MES |
| 11 | A7 | Temp2 | 9 | A19 | **I_SHUNT1_CMP** |
| 12 | A8 | Iin | 24 | A21 | I_SHUNT2_MES |
| 14 | A10 | Iout | 25 | A22 | **I_SHUNT2_CMP** |
| 15 | A11 | ADC_8 | 16 | A23 | VREF_ADC (VREFHI) |
| 18 | A12 | ADC_9 | 17 | A24 | VREFLO_SENSE |

Masses en A1, A5, A9, A13, A17, A20. A1 rejoint VSSA (broche 21).

### Rangée B — numérique, 1 × 32

| Broche | Position | Signal | Broche | Position | Signal |
|---|---|---|---|---|---|
| 3 | B3 | nRESET (XRSn) | 47 | B17 | I2C_SCL |
| 35 | B4 | BOOT_SEL | 63 | B18 | I2C_SDA |
| 52 | B5 | PWM1_A | 41 | B19 | SPI_CLK |
| 51 | B6 | PWM1_B | 33 | B20 | SPI_SIMO |
| 50 | B7 | PWM2_A | 34 | B21 | SPI_SOMI |
| 49 | B8 | PWM2_B | 42 | B22 | SPI_STE |
| 48 | B10 | PWM3_A | 29 | B24 | CAN_TX |
| 61 | B11 | PWM3_B | 30 | B25 | CAN_RX |
| 64 | B12 | PWM4_A | 31 | B26 | CMP_OUT1 |
| 57 | B13 | PWM4_B | 62 | B27 | CMP_OUT2 |
| 1 | B15 | UART_TX | 56 | B28 | CLB_OUT1 |
| 2 | B16 | UART_RX | 54 | B29 | CLB_OUT2 |
| | | | 32 | B30 | GPIO_1 |
| | | | 53 | B31 | GPIO_2 |
| | | | 55 | B32 | GPIO_3 |

Masses en B1, B9, B14, B23. +5V en B2.

### Hors connecteur

| Broche | PCB A — F280037 | PCB B — F28P551 |
|---|---|---|
| 36, 38 | TCK, TMS | idem |
| 37, 39 | TDO (GPIO37), TDI (GPIO35) | idem |
| 21 | VSSA | idem |
| 22 | VDDA 3,3 V | idem |
| 4, 44, 59 | VDD 1,2 V, découplage | idem |
| 43, 60 | VDDIO 3,3 V | idem |
| 5, 26, 45, 58 | VSS | idem |
| **27** | **VDD 1,2 V, découplage** | **LED bleue (GPIO20)** |
| **28** | **VDDIO 3,3 V** | **LED rouge (GPIO21)** |
| **40** | **LED rouge (GPIO32)** | pastille de test (GPIO32) |
| **46** | **LED bleue (GPIO39)** | **VREGENZ à VSS** |

Bilan : 45 broches au connecteur, 4 en JTAG, 13 en alimentation et 2 sur le
devkit pour le PCB A ; 45, 4, 11 et 4 pour le PCB B.

---

## 3. Alimentation

Deux LDO 3,3 V, alimentés par le 5 V venant du connecteur ou de l'USB.

| Rail | Broches | Découplage |
|---|---|---|
| **VDDIO 3,3 V** — LDO n°1 | 43, 60 *(+28 sur PCB A)* | 100 nF par broche |
| **VDDA 3,3 V** — LDO n°2 | 22 | ≥ 2,2 µF + 100 nF |
| **VDD 1,2 V** — régulateur interne | 4, 44, 59 *(+27 sur PCB A)* | ≈ 10 µF au total, **broches reliées entre elles** |
| VREFHI / VREFLO | 16, 17 | **≥ 2,2 µF entre les deux**, au plus près |

**VDD n'est pas alimenté.** C'est la sortie du régulateur interne, à découpler
seulement. Sur le PCB B, VREGENZ (broche 46) est reliée à VSS pour activer ce
régulateur ; le F280037 en 64 PM non-Q n'a pas cette broche, son régulateur est
toujours actif.

**OR-ing d'entrée** : deux Schottky, l'une depuis VBUS de l'USB, l'autre depuis
B2, réunies en entrée des deux LDO. Permet de faire tourner le devkit seul en
développement sans refouler de courant vers la carte de puissance.

**Masses** : VSS et VSSA réunies en un point unique près du boîtier, sous les
broches 21 et 26. Une seule masse au connecteur. Quatre couches recommandées,
pour un plan continu sous la zone analogique.

---

## 4. JTAG et reset

Embase **cTBP 10 points** : TCK 36, TDO 37, TMS 38, TDI 39, plus XRSn, 3,3 V et
masse.

**Ces MCU n'ont pas de broche TRSTn** — SPRSP61C le dit dans la description de
TMS. Prévoir un **rappel de 2,2 kΩ sur TMS vers VDDIO** : c'est lui qui maintient
le JTAG en reset pendant le fonctionnement normal. Ne pas reprendre le /TRST du
schéma F28027.

**Reset** : bouton-poussoir vers VSS sur XRSn (broche 3), rappel 2,2 à 10 kΩ vers
VDDIO, condensateur ≤ 100 nF vers VSS. La même broche sort en B3, attaquée **en
drain ouvert uniquement** par l'extérieur.

---

## 5. LED et cavalier de boot

Les LED sont posées sur les **E/S non communes**, ce qui rend le connecteur
identique à 100 % sur les deux PCB.

| | PCB A — F280037 | PCB B — F28P551 |
|---|---|---|
| LED bleue | GPIO39, broche 46 | GPIO20, broche 27 |
| LED rouge | GPIO32, broche 40 | GPIO21, broche 28 |

GPIO20 et GPIO21 sont des broches analogiques sur le F28P551 : le firmware doit
écrire `GPIOHAMSEL` pour les utiliser en numérique.

**Cavalier de mode boot sur GPIO24 (broche 35)**, également sorti en B4. Position
haute = Flash, position basse = boot SCI ROM. La configuration OTP retenue,
`BOOTPIN_CONFIG = 0x5AFF18FF`, n'active qu'une seule broche de sélection et
libère GPIO32. Essayer via `EMU_BOOTPIN_CONFIG` avant de brûler l'OTP.

---

## 6. Mécanique

| | |
|---|---|
| Boîtier | LQFP64 PM, 10 × 10 mm corps, 12 mm hors tout |
| Empreinte KiCad | `Package_QFP:LQFP-64_10x10mm_P0.5mm` |
| Rangée A | embase mâle 1 × 24, pas 2,54 mm |
| Rangée B | embase mâle 1 × 32, pas 2,54 mm |
| Entraxe des rangées | **25,4 mm** (10 pas) |
| Longueur | fixée par la rangée B : 32 × 2,54 = 81,3 mm |
| Carte | ≈ 85 × 28 mm, 4 couches |
| Horloge | interne, X1/X2 non câblés — GPIO18/GPIO19 libres pour le SPI |

Les embases sont mâles sous le devkit, femelles sur le shield, pour un retrait
sans outil. Le devkit doit se trouver **au-dessus de la zone commande** du
shield.

---

## 7. Nomenclature indicative

| Fonction | Composant |
|---|---|
| MCU | TMS320F280037CSPM ou TMS320F28P551SG5PM |
| LDO VDDIO | 3,3 V, ≥ 300 mA, faible bruit |
| LDO VDDA | 3,3 V, ≥ 100 mA, **faible bruit prioritaire** |
| OR-ing | 2 × Schottky, chute faible |
| USB | connecteur seul, alimentation de secours en développement |
| JTAG | embase cTBP 10 points, pas 1,27 mm |
| Reset | poussoir tactile + 10 kΩ + 100 nF |
| LED | 2 × 0603, résistances selon 4 mA |
| Découplage | 100 nF par broche d'alimentation, 10 µF sur VDD, 2,2 µF sur VDDA, 2,2 µF entre VREFHI et VREFLO |
| Cavalier boot | 1 × 3 points, pas 2,54 mm |

---

## 8. Points à trancher avant routage

- Valeur de VREFHI en mode externe : 2,5 V ou 3,0 V, selon la pleine échelle des
  AMC ratiométriques. Plage admissible, impédance de source et courant absorbé
  restent `à vérifier`.
- État au reset de GPIO39 sur le PCB A, pour que la LED bleue ne s'allume pas
  pendant le démarrage.
- Tenue de GPIO20 et GPIO21 en sortie sur le PCB B : le mode 20 mA du F28P551
  (`IO_DRVSEL`) n'est pas vérifié dans SPRSPC5, considérer 4 mA.
- Placement exact du point de jonction VSS/VSSA par rapport aux broches 21 et 26
  et à l'arrivée du +5V en B2.
- Choix de l'entraxe si vous préférez 22,86 mm : vérifier qu'il reste de la place
  pour les deux LDO, l'USB et l'embase JTAG autour d'un boîtier de 12 mm.
