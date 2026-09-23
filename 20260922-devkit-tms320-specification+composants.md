# Devkit TMS320 C2000 — spécification consolidée

Remplace tous les documents de brochage antérieurs. Deux PCB à partir d'un seul
schéma, `DEVKIT_C2000_A` pour le F280037CSPM et `DEVKIT_C2000_B` pour le
F28P551SG5PM. Connecteur 2 × 28, entraxe 25,4 mm.

Les 64 broches sont attribuées et vérifiées sur les deux variantes.

Tous les composants passifs en 0805 sauf indication.

---

## 1. Ce qui a changé depuis les premières versions

| Point | Avant | Maintenant |
|---|---|---|
| Cible | F28027 + deux 64 broches | **F280037 et F28P551 seuls** |
| Connecteur | 2 × 32, symétrique | **2 × 28, rangées symétriques** |
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

### Rangée A — analogique, 1 × 28

| Pos | Signal | Broche | Canaux ADC / note |
|---|---|---|---|
| A1 | GND | 21 (VSSA) | — |
| A2 | Vin | 6 | A6 |
| A3 | Vout | 7 | B2/C6 |
| A4 | GND | — | — |
| A5 | V1 | 8 | A3/B3/C5 |
| A6 | Temp1 | 10 | A15/B9/C7 |
| A7 | GND | — | — |
| A8 | Temp2 | 11 | A14/B14/C4 |
| A9 | Iin | 12 | A11/B10/C0 |
| A10 | GND | — | — |
| A11 | Iout | 14 | A1/B7 |
| A12 | ADC_8 | 15 | A0/B15/C15 |
| A13 | GND | — | — |
| A14 | ADC_9 | 18 | A12/C1 |
| A15 | ADC_10 | 19 | A7/C3 |
| A16 | GND | — | — |
| A17 | ADC_11 | 20 | A8/B0/C11 |
| A18 | ADC_12 | 23 | A4/B8/C14 |
| A19 | GND | — | — |
| A20 | I_SHUNT1_MES | 13 | A5/B12/C2 |
| A21 | GND | — | — |
| A22 | I_SHUNT1_CMP | 9 | A2/B6/C9 - CMP1_HP0 |
| A23 | GND | — | — |
| A24 | I_SHUNT2_MES | 24 | A9/B4/C8 |
| A25 | GND | — | — |
| A26 | I_SHUNT2_CMP | 25 | A10/B1/C10 - CMP2_HP3 |
| A27 | VREF_ADC | 16 | VREFHI |
| A28 | VREFLO_SENSE | 17 | VREFLO |

Dix masses pour dix-huit signaux. **Chaque ligne de shunt est encadrée de masses des deux côtés.** A1 rejoint VSSA (broche 21). VREF_ADC et VREFLO_SENSE forment une paire de référence en fin de rangée.

### Rangée B — numérique, 1 × 28

| Pos | Signal | Broche | GPIO, fonction et mux |
|---|---|---|---|
| B1 | GND | 5/26/45/58 | — |
| B2 | +5V | — | — |
| B3 | nRESET | 3 | XRSn |
| B4 | BOOT_SEL | 35 | GPIO24 mux0 - BMSP1 |
| B5 | PWM1_A | 52 | GPIO0 EPWM1_A mux1 |
| B6 | PWM1_B | 51 | GPIO1 EPWM1_B mux1 |
| B7 | PWM2_A | 50 | GPIO2 EPWM2_A mux1 |
| B8 | PWM2_B | 49 | GPIO3 EPWM2_B mux1 |
| B9 | GND | — | — |
| B10 | PWM3_A | 48 | GPIO4 EPWM3_A mux1 |
| B11 | PWM3_B | 61 | GPIO5 EPWM3_B mux1 |
| B12 | PWM4_A | 64 | GPIO6 EPWM4_A mux1 |
| B13 | PWM4_B | 57 | GPIO7 EPWM4_B mux1 |
| B14 | GND | — | — |
| B15 | UART_TX | 1 | GPIO29 SCIA_TX mux1 |
| B16 | UART_RX | 2 | GPIO28 SCIA_RX mux1 |
| B17 | I2C_SCL | 47 | GPIO8 I2CA_SCL mux9 |
| B18 | I2C_SDA | 63 | GPIO10 I2CA_SDA mux9 |
| B19 | SPI_CLK | 41 | GPIO18 SPIA_CLK mux1 |
| B20 | SPI_SIMO | 33 | GPIO16 SPIA_SIMO mux1 |
| B21 | SPI_SOMI | 34 | GPIO17 SPIA_SOMI mux1 |
| B22 | SPI_STE | 42 | GPIO19 SPIA_STE mux1 |
| B23 | GND | — | — |
| B24 | CAN_TX | 29 | GPIO13 MCAN_TX mux3 |
| B25 | CAN_RX | 30 | GPIO12 MCAN_RX mux3 |
| B26 | CMP_OUT | 31 | GPIO11 OUTPUTXBAR7 mux3 |
| B27 | CLB_OUT | 56 | GPIO22 CLB_OUTPUTXBAR1 mux10 |
| B28 | GPIO_1 | 32 | GPIO33 mux0 - nFAULT |

Vingt-quatre signaux, quatre masses. Retirés par rapport à la version 24/32 : CMP_OUT2, CLB_OUT2, GPIO_2 et GPIO_3 — les broches 62, 54, 53 et 55 deviennent des pastilles de test. Un seul OUTPUTXBAR peut agréger plusieurs sources CMPSS, et une sortie CLB suffit à l'observation.

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

Led bleue/rouge 3 broches 3mm, avec resistances 10k

Bilan : 41 broches au connecteur, 4 en JTAG, 4 en pastilles de test, plus
alimentations et LED.

---

## 3. Alimentation

Deux LDO 3,3 V, alimentés par le 5 V venant du connecteur ou de l'USB.

MCP1700 + 2x10uF (in/out)
alimentation usb? l'alimentaton secondaire arrive par le connecteur jtag

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

Embase **tag-connect 2050 10 points** : TCK 36, TDO 37, TMS 38, TDI 39, plus XRSn, 3,3 V et
masse.

**Ces MCU n'ont pas de broche TRSTn** — SPRSP61C le dit dans la description de
TMS. Prévoir un **rappel de 2,2 kΩ sur TMS vers VDDIO** : c'est lui qui maintient
le JTAG en reset pendant le fonctionnement normal. Ne pas reprendre le /TRST du
schéma F28027. Verifier ce fonctionnement/cette information puyisque la broche 3 est connectée à nRST du jtag (TRST)

**Reset** : bouton-poussoir vers VSS sur XRSn (broche 3), rappel 2,2 à 10 kΩ vers
VDDIO, condensateur ≤ 100 nF vers VSS. La même broche sort en B3, attaquée **en
drain ouvert uniquement** par l'extérieur.

remplacer le bouton par un connecteur 2 broches 2,54mm standard + cavalier.

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

ce cavalier est il nécessaire pour des devkit de développement?

---

## 6. Mécanique

| | |
|---|---|
| Boîtier | LQFP64 PM, 10 × 10 mm corps, 12 mm hors tout |
| Empreinte KiCad | `Package_QFP:LQFP-64_10x10mm_P0.5mm` |
| Rangée A | embase mâle 1 × 28, pas 2,54 mm |
| Rangée B | embase mâle 1 × 28, pas 2,54 mm |
| **Entraxe des rangées** | **25,4 mm** (10 pas) |
| Longueur | 28 × 2,54 = 71,1 mm |
| Carte | ≈ 75 × 28 mm, 4 couches |
| Horloge | interne, X1/X2 non câblés — GPIO18/GPIO19 libres pour le SPI |

Embases mâles sous le devkit, femelles sur le shield, pour un retrait sans
outil. Le devkit se place **au-dessus de la zone commande** du shield.

### Détrompage

Les deux rangées faisant désormais la même longueur, la géométrie n'assure plus
le détrompage. Prévoir une clé : position obturée aux extrémités, ou ergot sur
le support. Sans elle, un montage à l'envers met le +5V de B2 sur VSSA.

### Cohabitation avec l'ESP32 sur le shield

L'ESP32-C6-DevKitC-1 a ses propres cotes, relevées dans son plan d'implantation
v1.2 : **entraxe 22,86 mm**, carte 51,8 × 25,4 mm, embases J1 et J3 au pas
2,54 mm. Le 1,27 mm mentionné sur le plan concerne J2 et J4, l'empreinte du
module, sans objet ici.

Le shield porte donc **deux entraxes différents** : 25,4 mm pour le devkit C2000,
22,86 mm pour l'ESP32. Deux références de support à approvisionner, mais le
dégagement de routage autour du LQFP64 est préservé — c'est le choix retenu.

## 7. Nomenclature indicative

| Fonction | Composant |
|---|---|
| MCU | TMS320F280037CSPM ou TMS320F28P551SG5PM |
| LDO VDDIO | 3,3 V, ≥ 300 mA, faible bruit | mcp1700 3.3V + 2 condensateurs 10uF
| LDO VDDA | 3,3 V, ≥ 100 mA, **faible bruit prioritaire** | mcp1700 3.3V + 2 condensateurs 10uF
| OR-ing | 2 × Schottky, chute faible | sot23 simple diode
| USB | connecteur seul, alimentation de secours en développement | remplace par du 3.3V issu du connecteur JTAG (vddio)
| JTAG | embase tag connect 2050 10 points|
| Reset | cavalier 2x2,54mm standard + 10 kΩ + 100 nF |
| LED | 1x3mm 2 couleurs haute luminosité, résistances 10k |
| Découplage | 100 nF par broche d'alimentation, 10 µF sur VDD, 2,2 µF sur VDDA, 2,2 µF entre VREFHI et VREFLO |
| Cavalier boot | 1 × 3 points, pas 2,54 mm | si nécessaire

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
