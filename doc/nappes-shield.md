# Nappes shield ↔ carte de puissance, et répartition des cartes

Ce document décrit ce qui relie le shield à la carte de puissance. **Le
connecteur devkit, le brochage des 64 broches, l'alimentation, le JTAG et la
mécanique sont dans [`spec-devkit.md`](spec-devkit.md)**, qui fait autorité.

## 1. Les quatre nappes

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

## 2. Répartition des cartes

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

