# Brochage définitif — devkit C2000 et nappes shield ↔ puissance

Intègre tous les arbitrages : I2C conservé, reset et sélection de boot
réintroduits, voies shunt dédoublées, isolation et NCM3 sur la carte de
puissance, OLED en SPI sur l'ESP32.

Connecteur devkit : **deux rangées de 28**, soit 56 positions. Identique sur les
deux PCB (F280037CSPM et F28P551SG5PM).

> **Ce document est reconstruit depuis `lib/C2000_Devkit_Connectors.kicad_sym`**,
> qui est la bibliothèque réellement utilisée par les trois schémas. En cas de
> doute, c'est elle qui tranche : les positions ci-dessous en sont extraites,
> pas recopiées.

## 0. Pourquoi deux rangées égales

La version précédente répartissait 24 + 32. Le passage au symétrique coûte
quatre signaux, retirés faute de place : `CMP_OUT2`, `CLB_OUT2`, `GPIO_2` et
`GPIO_3`. Les broches MCU correspondantes — 62, 54, 53 et 55 — deviennent les
pastilles de test `TP_PIN62`, `TP_PIN54`, `TP_PIN53` et `TP_PIN55`.
`CMP_OUT1` et `CLB_OUT1` perdent leur indice et deviennent `CMP_OUT` et
`CLB_OUT`.

**Les deux rangées étant identiques, prévoir une clé mécanique** : position
obturée aux extrémités, ou ergot sur le support. L'asymétrie 24/32 assurait le
détrompage toute seule, ce n'est plus le cas — une carte retournée branche le
+5 V sur une entrée analogique.

---

## 1. Rangée A — analogique, 1 × 28

| Pos | Signal | Broche | Canaux ADC | Pos | Signal | Broche | Canaux ADC |
|---|---|---|---|---|---|---|---|
| A1 | GND | 21 (VSSA) | — | A15 | ADC_10 | 19 | A7, C3 |
| A2 | Vin | 6 | A6 | A16 | GND | — | — |
| A3 | Vout | 7 | B2, C6 | A17 | ADC_11 | 20 | A8, B0, C11 |
| A4 | GND | — | — | A18 | ADC_12 | 23 | A4, B8, C14 |
| A5 | V1 | 8 | A3, B3, C5 | A19 | GND | — | — |
| A6 | Temp1 | 10 | A15, B9, C7 | A20 | **I_SHUNT1_MES** | 13 | A5, B12, C2 |
| A7 | GND | — | — | A21 | GND | — | — |
| A8 | Temp2 | 11 | A14, B14, C4 | A22 | **I_SHUNT1_CMP** | **9** | A2, B6, C9 |
| A9 | Iin | 12 | A11, B10, C0 | A23 | GND | — | — |
| A10 | GND | — | — | A24 | **I_SHUNT2_MES** | 24 | A9, B4, C8 |
| A11 | Iout | 14 | A1, B7 | A25 | GND | — | — |
| A12 | ADC_8 | 15 | A0, B15, C15 | A26 | **I_SHUNT2_CMP** | **25** | A10, B1, C10 |
| A13 | GND | — | — | A27 | **VREF_ADC** | 16 | VREFHI |
| A14 | ADC_9 | 18 | A12, C1 | A28 | **VREFLO_SENSE** | 17 | VREFLO |

18 signaux, 10 masses. Les 16 voies ADC du boîtier sortent toutes.

**Masse renforcée autour des shunts.** A19 à A26 alternent strictement masse et
signal : chaque voie shunt est encadrée des deux côtés. Les quatre positions de
masse gagnées sur la rangée B servent d'abord à ça.

**Voies shunt dédoublées.** La sortie de chaque AMC0300R est reprise deux fois
sur le shield : un chemin filtré vers la voie de mesure, un chemin direct vers la
voie comparateur. Le filtre anti-repliement ne retarde plus le déclenchement de
la Trip Zone, et un défaut sur le filtre ne désarme pas la protection.

| Voie | Broche | CMPSS | Rôle |
|---|---|---|---|
| I_SHUNT1_CMP | 9 | **CMP1_HP0** | seuil DAC interne → Trip Zone, Rs ≤ 50 Ω, sans filtre |
| I_SHUNT1_MES | 13 | — | mesure ADC, filtrée |
| I_SHUNT2_CMP | 25 | **CMP2_HP3** | CMPSS-2, chemin direct |
| I_SHUNT2_MES | 24 | — | mesure ADC, filtrée |

**VREF_ADC et VREFLO_SENSE forment une paire adjacente**, en A27 et A28. La
conversion est ramenée à (VIN − VREFLO) / (VREFHI − VREFLO) : toute chute
ohmique entre la référence des AMC0300R et VREFLO devient un décalage sur les
16 voies. Le shield bufferise VREF_ADC par un suiveur rail-to-rail et renvoie la
paire sur la nappe. Ne pas insérer de masse entre les deux.

Voies libres : A12, A14, A15, A17, A18 — cinq de marge sur les neuf demandées.

---

## 2. Rangée B — numérique, 1 × 28

| A14 | ADC_9 | 18 | A12, C1 | A28 | **VREFLO_SENSE** | 17 | VREFLO |

| Pos | Signal | GPIO | Broche | Mux | Pos | Signal | GPIO | Broche | Mux |
|---|---|---|---|---|---|---|---|---|---|
| B1 | GND | — | 5/26/45/58 | — | B15 | UART_TX | GPIO29 | 1 | 1 |
| B2 | **+5V** | — | nappe | — | B16 | UART_RX | GPIO28 | 2 | 1 |
| B3 | **nRESET** | — | 3 (XRSn) | — | B17 | I2C_SCL | GPIO8 | 47 | 9 |
| B4 | **BOOT_SEL** | GPIO24 | 35 | 0 | B18 | I2C_SDA | GPIO10 | 63 | 9 |
| B5 | PWM1_A | GPIO0 | 52 | 1 | B19 | SPI_CLK | GPIO18 | 41 | 1 |
| B6 | PWM1_B | GPIO1 | 51 | 1 | B20 | SPI_SIMO | GPIO16 | 33 | 1 |
| B7 | PWM2_A | GPIO2 | 50 | 1 | B21 | SPI_SOMI | GPIO17 | 34 | 1 |
| B8 | PWM2_B | GPIO3 | 49 | 1 | B22 | SPI_STE | GPIO19 | 42 | 1 |
| B9 | GND | — | — | — | B23 | GND | — | — | — |
| B10 | PWM3_A | GPIO4 | 48 | 1 | B24 | CAN_TX | GPIO13 | 29 | 3 |
| B11 | PWM3_B | GPIO5 | 61 | 1 | B25 | CAN_RX | GPIO12 | 30 | 3 |
| B12 | PWM4_A | GPIO6 | 64 | 1 | B26 | CMP_OUT | GPIO11 | 31 | 3 |
| B13 | PWM4_B | GPIO7 | 57 | 1 | B27 | CLB_OUT | GPIO22 | 56 | 10 |
| B14 | GND | — | — | — | B28 | GPIO_1 | GPIO33 | 32 | 0 |

24 signaux, 4 masses. Toutes les positions de mux sont identiques sur les deux
MCU, vérifiées dans les deux tableaux *Pin Attributes*.

**B3 et B4 forment le chemin de récupération.** L'ESP32 met BOOT_SEL à 0, impulse
nRESET, et le composant entre en boot SCI ROM sur GPIO29 / GPIO28 — c'est-à-dire
sur les mêmes broches que UART_TX / UART_RX en B15 / B16. Aucune ligne
supplémentaire. En fonctionnement normal, BOOT_SEL reste à 1 et l'ESP32 met à
jour par FOTA sans toucher à ces deux lignes.

nRESET doit être attaqué **en drain ouvert uniquement** : le MCU tire lui-même
cette ligne à zéro sur watchdog et sur brownout.

**B15 / B16 servent trois usages** sur les mêmes fils : la télémétrie courante
vers l'ESP32, la commande FOTA pendant que l'application tourne, et le boot ROM
en récupération.

---

## 3. Nappes shield ↔ carte de puissance

Quatre connecteurs **2 × 8**, nappes 16 conducteurs, **alternance signal / masse
stricte 1:1** sur les quatre. Aucune ligne d'alimentation dans les nappes.

### ADC-1 — mesures tension et température

| | | | | | | | |
|---|---|---|---|---|---|---|---|
| 1 GND | 2 **Vin** | 3 GND | 4 **Vout** | 5 GND | 6 **V1** | 7 GND | 8 **Temp1** |
| 9 GND | 10 **Temp2** | 11 GND | 12 **Iin** | 13 GND | 14 **Iout** | 15 GND | 16 **réserve 1** |

### ADC-2 — shunts, référence, réserves

| | | | | | | | |
|---|---|---|---|---|---|---|---|
| 1 GND | 2 **I_shunt1** | 3 GND | 4 **I_shunt2** | 5 GND | 6 **VREF_ADC** | 7 **VREFLO_SENSE** | 8 GND |
| 9 GND | 10 **réserve 2** | 11 GND | 12 **réserve 3** | 13 GND | 14 **réserve 4** | 15 GND | 16 **réserve 5** |

VREF_ADC et VREFLO_SENSE occupent les positions 6 et 7, adjacentes : c'est une
paire de référence, pas deux signaux indépendants. Le shield bufferise VREF_ADC
par un suiveur rail-to-rail avant de l'envoyer.

Les cinq réserves correspondent exactement aux cinq voies ADC libres du
connecteur devkit — A12, A14, A15, A17, A18. Une voie ajoutée plus tard se câble
de bout en bout sans retoucher aucune carte.

### PWM — commandes rapides

| | | | | | | | |
|---|---|---|---|---|---|---|---|
| 1 GND | 2 **PWM1_A** | 3 GND | 4 **PWM1_B** | 5 GND | 6 **PWM2_A** | 7 GND | 8 **PWM2_B** |
| 9 GND | 10 **PWM3_A** | 11 GND | 12 **PWM3_B** | 13 GND | 14 **PWM4_A** | 15 GND | 16 **PWM4_B** |

Seules lignes à fronts rapides de l'ensemble. PWM3 et PWM4 restent en réserve, en
paires complémentaires HRPWM avec temps mort matériel.

### GPIO — commandes lentes, sécurité, service

| | | | | | | | |
|---|---|---|---|---|---|---|---|
| 1 GND | 2 **Stage1_EN** | 3 GND | 4 **Stage2_EN** | 5 GND | 6 **HV_EN** | 7 GND | 8 **Discharge** |
| 9 GND | 10 **CMP_OUT** | 11 GND | 12 **nFAULT** | 13 GND | 14 **I2C_SCL** | 15 GND | 16 **I2C_SDA** |

`nFAULT` remonte un défaut de la carte de puissance vers GPIO_1 (B28).
`CMP_OUT` sort le drapeau de défaut agrégé du C2000. L'I2C reste disponible pour
un capteur de température ou une EEPROM de calibration sur la carte de puissance.

### Alimentation — connecteur séparé

Les quatre nappes étant saturées par l'alternance 1:1, le **+5V commande n'y a
pas sa place** — et c'est mieux ainsi. Les 500 mA que consomment les deux
devkits, l'OLED et le conditionnement analogique ne doivent pas partager leur
retour avec les masses de référence des voies ADC : c'était précisément le
mécanisme d'erreur à éviter.

Prévoir un **connecteur d'alimentation dédié**, deux ou quatre voies, dimensionné
pour 1 A — Micro-Fit, KK 396 ou bornier à vis selon vos habitudes. Deux
conducteurs suffisent, quatre permettent de doubler +5V et retour et de diviser
la chute par deux.

## 4. Répartition finale

**Carte de puissance** — conversion, barrière d'isolation, tous les isolateurs
(AMC0311S, AMC0300R, ISO7710, DPC817), INA293A2 et shunts en connexion Kelvin,
**NCM3S1205MC**, régulateur 5 V commande depuis l'entrée 10-24 V, régulateur
3,3 V pour le côté sortie des isolateurs.

**Shield** — support mécanique des deux devkits, adaptation de brochage,
conditionnement analogique (filtres anti-repliement, suiveur VREF, dédoublement
des voies shunt), protections, deux branches d'alimentation séparées, embase
nappe OLED. Aucun composant isolé.

**Devkit C2000** — MCU, deux LDO 3,3 V (VDDIO et VDDA), JTAG, bouton reset, deux
LED, cavalier de boot.

**Devkit ESP32** — Wi-Fi, hôte FOTA, écran OLED en SPI sur nappe.

---

## 5. Devkit — ce qui reste hors connecteur

| Élément | F280037CSPM | F28P551SG5PM |
|---|---|---|
| JTAG cTBP 10 pts | TCK 36, TDO 37, TMS 38, TDI 39 | idem |
| LED bleue | GPIO39 — br. 46 | GPIO20 — br. 27 |
| LED rouge | GPIO32 — br. 40 | GPIO21 — br. 28 |
| Broche 35 (GPIO24) | BOOT_SEL, cavalier + B4 | idem |
| Broche 40 (GPIO32) | LED rouge | pastille de test |
| Broche 46 | GPIO39 → LED bleue | **VREGENZ à VSS** |
| Broches 27, 28 | VDD, VDDIO | GPIO20, GPIO21 → LED |
| LDO 3,3 V n°1 | VDDIO 43, 60 (+28) | VDDIO 43, 60 |
| LDO 3,3 V n°2 | VDDA 22, ≥ 2,2 µF | idem |
| VDD 1,2 V interne | 4, 44, 59 (+27), ≈ 10 µF | 4, 44, 59 |
| VREFHI / VREFLO | 16, 17, ≥ 2,2 µF entre les deux | idem |

**Pas de broche TRSTn sur ces MCU.** Rappel de 2,2 kΩ sur TMS vers VDDIO.

**BOOTPIN_CONFIG à programmer en OTP** : Key = 0x5A, BMSP1 = 24 (GPIO24),
BMSP0 = 0xFF, BMSP2 = 0xFF. Une seule broche de sélection, GPIO32 libéré pour la
LED. Essayer d'abord via `EMU_BOOTPIN_CONFIG` avant de brûler l'OTP.

---

## 6. Reste à vérifier

- Nombre de banques Flash sur le F280037CSPM et le F28P551SG5PM, pour le FOTA.
- Débit SCI maximal accepté par l'autobaud du bootloader, qui fixe la durée
  d'indisponibilité pendant la mise à jour.
- Caractéristiques de sortie des AMC0311S et AMC0300R : impédance, pleine
  échelle, bande passante — pour dimensionner les filtres sous la contrainte
  Rs ≤ 50 Ω.
- Courant d'entrée du REFIN des AMC0300R, pour le suiveur.
- Choix de VREFHI externe : 2,5 V ou 3,0 V, selon la pleine échelle des AMC.
- Matériel LFU dédié sur le F28P551 (`à vérifier` : documenté pour le F28003x).
