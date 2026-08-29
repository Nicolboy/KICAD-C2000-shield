# Connecteur devkit C2000 — 2 × 24

Dimensionné sur le besoin réel du shield d'isolation, pas sur le nombre de
broches du boîtier. 48 positions, carte ≈ 64 × 28 mm — format ESP32 devkit.

Identique sur les deux PCB (F280037 et F28P551), 48 positions sur 48.

---

## Rangée A — analogique, 1 × 24

| Pos | Signal | Broche | Pos | Signal | Broche |
|---|---|---|---|---|---|
| A1 | GND | — | A13 | GND | — |
| A2 | ADC_1 | 6 | A14 | ADC_9 | 15 |
| A3 | ADC_2 | 7 | A15 | ADC_10 | 18 |
| A4 | GND | — | A16 | GND | — |
| A5 | ADC_3 | 8 | A17 | **I_SHUNT1** | **9** (CMP1_HP0) |
| A6 | ADC_4 | 10 | A18 | GND | — |
| A7 | GND | — | A19 | **I_SHUNT2** | **25** (CMP2_HP3) |
| A8 | ADC_5 | 11 | A20 | GND | — |
| A9 | ADC_6 | 12 | A21 | ADC_11 | 19 |
| A10 | GND | — | A22 | GND | — |
| A11 | ADC_7 | 13 | A23 | **VREF_ADC** | 16 (VREFHI) |
| A12 | ADC_8 | 14 | A24 | GND | — |

11 voies simples + 2 voies I_SHUNT + la référence. Le shield en demande 7
simples et 2 shunts : il reste 4 voies de marge. Masse toutes les deux lignes,
et masse isolante de part et d'autre de chaque I_SHUNT et de VREF_ADC.

---

## Rangée B — numérique, 1 × 24

| Pos | Signal | GPIO | Broche | Mux | Pos | Signal | GPIO | Broche | Mux |
|---|---|---|---|---|---|---|---|---|---|
| B1 | GND | — | 5/26/45/58 | — | B13 | GPIO_4 | GPIO7 | 57 | 0 |
| B2 | **+5V** | — | USB | — | B14 | GND | — | — | — |
| B3 | **nRESET** | — | 3 (XRSn) | — | B15 | UART_TX | GPIO29 | 1 | 1 |
| B4 | GND | — | — | — | B16 | UART_RX | GPIO28 | 2 | 1 |
| B5 | PWM1_A | GPIO0 | 52 | 1 | B17 | I2C_SCL | GPIO8 | 47 | 9 |
| B6 | PWM1_B | GPIO1 | 51 | 1 | B18 | I2C_SDA | GPIO10 | 63 | 9 |
| B7 | PWM2_A | GPIO2 | 50 | 1 | B19 | SPI_CLK | GPIO18 | 41 | 1 |
| B8 | PWM2_B | GPIO3 | 49 | 1 | B20 | SPI_SIMO | GPIO16 | 33 | 1 |
| B9 | GND | — | — | — | B21 | SPI_SOMI | GPIO17 | 34 | 1 |
| B10 | GPIO_1 | GPIO4 | 48 | 0 | B22 | SPI_STE | GPIO19 | 42 | 1 |
| B11 | GPIO_2 | GPIO5 | 61 | 0 | B23 | CMP_OUT | GPIO11 | 31 | 3 |
| B12 | GPIO_3 | GPIO6 | 64 | 0 | B24 | CLB_OUT | GPIO22 | 56 | 10 |

**B10 à B13 sont à double usage.** En GPIO simples, ce sont les quatre commandes
du shield : Stage1_EN, Stage2_EN, HV_EN, Discharge. En mux 1, ce sont
`EPWM3_A`, `EPWM3_B`, `EPWM4_A`, `EPWM4_B` — soit **deux paires HRPWM
complémentaires de réserve**, sans coûter une seule position. C'est le
compromis qui permet de descendre à 24.

---

## Ce qui a été retiré, et pourquoi

| Retiré | Motif |
|---|---|
| CAN-FD (2 br.) | absent du cahier des charges du shield |
| 5 voies ADC (2 br. → 11 restantes) | 9 demandées, 11 offertes |
| 1 sortie comparateur | un seul OUTPUTXBAR peut agréger plusieurs sources CMPSS |
| 1 sortie CLB | une suffit pour l'observation |
| 4 GPIO génériques | remplacés par le double usage B10-B13 |
| Masses excédentaires | 14 masses au lieu de 19, densité conservée côté analogique |

Passage de 64 à 48 positions. Les broches non exportées restent accessibles en
pastilles de test sur le devkit : broches 29, 30, 32, 40, 53, 54, 55, 62 côté
numérique, et 20, 23, 24 côté analogique.

---

## Devkit

| Élément | Broches |
|---|---|
| JTAG cTBP 10 pts | TCK 36, TDO 37, TMS 38, TDI 39 — rappel **2,2 kΩ sur TMS vers VDDIO**, pas de TRSTn sur ces MCU |
| Bouton reset | XRSn 3, rappel 2,2–10 kΩ vers VDDIO, condensateur ≤ 100 nF vers VSS |
| LED bleue | GPIO39 br. 46 *(PCB F280037)* / GPIO20 br. 27 *(PCB F28P551)* |
| LED rouge | GPIO24 br. 35 *(F280037)* / GPIO21 br. 28 *(F28P551)* |
| LDO 3,3 V n°1 | VDDIO 43, 60 (+28 sur PCB F280037), 100 nF par broche |
| LDO 3,3 V n°2 | VDDA 22, ≥ 2,2 µF |
| VDD 1,2 V *(interne)* | 4, 44, 59 (+27 sur PCB F280037), ≈ 10 µF total, broches reliées entre elles |
| VREGENZ | br. 46 à VSS *(PCB F28P551 uniquement)* |
| VREFHI / VREFLO | 16, 17, ≥ 2,2 µF entre les deux |
| VSS / VSSA | réunies en un point unique près du boîtier ; une seule masse au connecteur |

nRESET doit être attaqué **en drain ouvert uniquement** par le shield : le MCU
tire lui-même cette ligne à zéro sur watchdog et sur brownout.

---

## Reste à vérifier

- Broches de mode de démarrage des deux MCU (`à vérifier`, manuel technique).
  GPIO24 porte une LED : prévoir un cavalier.
- Retour de VREF_ADC : la référence revient par GND au connecteur alors que
  VREFLO est réuni à VSSA sur le devkit. Placer le point de jonction unique
  VSS/VSSA pour que le REFIN des AMC0300R voie la même référence que le
  convertisseur.
- VREFHI en mode externe : plage, impédance de source, courant.
- Courant de sortie des GPIO : mode 20 mA du F28P551 non vérifié dans SPRSPC5,
  considérer 4 mA. Les DPC817 à 5 mA demandent un buffer côté shield.
- État au reset de GPIO39 (LED, PCB F280037).
