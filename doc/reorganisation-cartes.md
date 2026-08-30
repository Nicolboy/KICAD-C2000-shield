# 2026-08-30 — Réorganisation des cartes : dossier de reprise firmware

Document destiné aux agents firmware **ESP32** et **TMS320 C2000**. Il fixe
l'architecture matérielle, le brochage, la configuration de boot et le protocole
de mise à jour. Tout ce qui est marqué `à vérifier` n'a pas été confirmé dans une
datasheet ou un manuel technique et ne doit pas être codé en dur.

**Sources vérifiées**
SPRSP61C (datasheet F28003x) · SPRSPC5 (datasheet F28P55x) ·
SPRUIW9C (TRM F28003x) · SPRUJF8 (TRM F28P55x) · TIDUEY4E (TIDM-02011, LFU/FOTA).

---

## 1. Architecture

Quatre cartes, une seule barrière galvanique.

```
  ┌───────────────┐   ┌───────────────┐
  │ DEVKIT C2000  │   │ DEVKIT ESP32  │      OLED SSD1306
  │ F280037  ou   │   │ Wi-Fi, hôte   │──SPI──▶ (nappe)
  │ F28P551       │   │ FOTA          │
  └───────┬───────┘   └───────┬───────┘
          │  56 pos.          │
  ┌───────┴───────────────────┴───────────────────────────┐
  │ SHIELD — support, adaptation de brochage,             │
  │ conditionnement ADC, filtres RC, suiveur VREF,        │
  │ dédoublement des voies shunt, 2 branches d'alim       │
  └───────┬───────────────────────────────────────────────┘
          │  4 nappes 2×8  +  2 connecteurs d'alim en parallèle
  ┌───────┴───────────────────────────────────────────────┐
  │ CARTE DE PUISSANCE                                    │
  │ ┌─── commande ───┬─ BARRIÈRE ─┬─── HT 200-500 V ───┐  │
  │ │ régul. 5V/3V3  │ AMC0311S×5 │ boost 1 : →80 V    │  │
  │ │ depuis 10-24 V │ AMC0300R×3 │ boost 2 : →500 V   │  │
  │ │                │ ISO7710×2  │ shunts, INA293A2   │  │
  │ │                │ DPC817×4   │                    │  │
  │ │                │ NCM3S1205MC│                    │  │
  │ └────────────────┴────────────┴────────────────────┘  │
  └───────────────────────────────────────────────────────┘
```

**Le côté commande ne voit jamais plus de 3,3 V.** Toute l'isolation est sur la
carte de puissance. Le shield ne porte aucun composant isolé.

**Alimentation** : la carte de puissance génère tout depuis son entrée 10-24 V.
Le 5 V commande arrive au shield par deux connecteurs en parallèle, réunis en un
point unique, puis se sépare en deux branches — ESP32 + OLED d'un côté,
conditionnement analogique de l'autre. Le devkit C2000 fabrique localement
VDDIO 3,3 V et VDDA 3,3 V par deux LDO. **VDD 1,2 V est produit par le régulateur
interne du MCU et ne doit jamais être alimenté.**

---

## 2. Les deux MCU sont interchangeables

Boîtier LQFP64 PM. **Toutes les fonctions ci-dessous existent sur la même broche
et à la même position de mux sur les deux composants** — une seule table
d'initialisation du mux suffit.

| | F280037CSPM | F28P551SG5PM |
|---|---|---|
| Fréquence | 120 MHz | 160 MHz |
| Flash | 256 KB | 512 KB |
| ADC | 3 modules | 5 modules |
| ePWM HRPWM | ePWM1 à 4 | 12 canaux |
| NPU | non | oui |
| VREGENZ | **absent** (VREG toujours actif) | broche 46, à VSS |
| Broches 27, 28 | VDD, VDDIO | GPIO20, GPIO21 |
| Broche 46 | GPIO39 | VREGENZ |

Ces trois broches sont les seules différences. Elles restent sur le devkit et ne
sortent pas au connecteur — le firmware n'a pas à s'en préoccuper, sauf pour les
LED (voir §7).

---

## 3. Brochage numérique — rangée B (1 × 32)

| Pos | Signal | GPIO | Broche | **Mux** | Périphérique |
|---|---|---|---|---|---|
| B3 | nRESET | — | 3 | — | XRSn, drain ouvert |
| B4 | BOOT_SEL | GPIO24 | 35 | 0 | BMSP1 |
| B5 | PWM1_A | GPIO0 | 52 | **1** | EPWM1_A, HRPWM |
| B6 | PWM1_B | GPIO1 | 51 | **1** | EPWM1_B, HRPWM |
| B7 | PWM2_A | GPIO2 | 50 | **1** | EPWM2_A, HRPWM |
| B8 | PWM2_B | GPIO3 | 49 | **1** | EPWM2_B, HRPWM |
| B10 | PWM3_A | GPIO4 | 48 | **1** | EPWM3_A, HRPWM |
| B11 | PWM3_B | GPIO5 | 61 | **1** | EPWM3_B, HRPWM |
| B12 | PWM4_A | GPIO6 | 64 | **1** | EPWM4_A, HRPWM |
| B13 | PWM4_B | GPIO7 | 57 | **1** | EPWM4_B, HRPWM |
| B15 | UART_TX | GPIO29 | 1 | **1** | SCIA_TX |
| B16 | UART_RX | GPIO28 | 2 | **1** | SCIA_RX |
| B17 | I2C_SCL | GPIO8 | 47 | **9** | I2CA_SCL |
| B18 | I2C_SDA | GPIO10 | 63 | **9** | I2CA_SDA |
| B19 | SPI_CLK | GPIO18 | 41 | **1** | SPIA_CLK |
| B20 | SPI_SIMO | GPIO16 | 33 | **1** | SPIA_SIMO / PICO |
| B21 | SPI_SOMI | GPIO17 | 34 | **1** | SPIA_SOMI / POCI |
| B22 | SPI_STE | GPIO19 | 42 | **1** | SPIA_STE / PTE |
| B24 | CAN_TX | GPIO13 | 29 | **3** | MCAN_TX |
| B25 | CAN_RX | GPIO12 | 30 | **3** | MCAN_RX |
| B26 | CMP_OUT1 | GPIO11 | 31 | **3** | OUTPUTXBAR7 |
| B27 | CMP_OUT2 | GPIO9 | 62 | **3** | OUTPUTXBAR6 |
| B28 | CLB_OUT1 | GPIO22 | 56 | **10** | CLB_OUTPUTXBAR1 |
| B29 | CLB_OUT2 | GPIO23 | 54 | **10** | CLB_OUTPUTXBAR3 |
| B30 | GPIO_1 | GPIO33 | 32 | 0 | ← nFAULT carte puissance |
| B31 | GPIO_2 | GPIO40 | 53 | 0 | libre |
| B32 | GPIO_3 | GPIO41 | 55 | 0 | libre |

Masses en B1, B9, B14, B23. +5V en B2.

**Attribution applicative des sorties de commande**, via la nappe GPIO :
Stage1_EN, Stage2_EN, HV_EN, Discharge. Elles occupent quatre des lignes
disponibles — à figer côté firmware selon le câblage retenu sur le shield.

**Les paires ePWM sont complémentaires**, même module A/B, temps mort matériel
disponible. PWM1 et PWM2 pilotent les deux étages boost, PWM3 et PWM4 sont en
réserve.

---

## 4. Brochage analogique — rangée A (1 × 24)

Canaux ADC réels, identiques sur les deux MCU sauf mentions :

| Pos | Signal | Broche | Canaux F280037 | Canaux F28P551 | CMPSS disponibles |
|---|---|---|---|---|---|
| A2 | Vin | 6 | A6 | A6, D14, E14 | CMP1_HP2 |
| A3 | Vout | 7 | B2, C6 | B2, C6, E12 | CMP3_HP0 |
| A4 | V1 | 8 | A3, B3, C5 | A3, B3, C5 | CMP3_HP3, CMP3_HP5 |
| A6 | Temp1 | 10 | A15, B9, C7 | idem | CMP1_HP3 |
| A7 | Temp2 | 11 | A14, B14, C4 | idem | CMP3_HP4 |
| A8 | Iin | 12 | A11, B10, C0 | idem | CMP1_HP1 |
| A10 | Iout | 14 | A1, B7 | A1, B7, D11 | CMP1_HP4 |
| A11 | ADC_8 | 15 | A0, B15, C15 | idem | CMP3_HP2 |
| A12 | ADC_9 | 18 | A12, C1 | A12, C1, E11 | CMP2_HP1, CMP4_HP2 |
| A14 | ADC_10 | 19 | A7, C3 | A7, B30, C3, D12, E30 | CMP4_HP1 |
| A15 | ADC_11 | 20 | A8, B0, C11 | idem | CMP2_HP4, CMP4_HP4 |
| A16 | ADC_12 | 23 | A4, B8, C14 | idem | CMP2_HP0, CMP4_HP3 |
| A18 | **I_SHUNT1_MES** | 13 | A5, B12, C2 | idem | — (chemin filtré) |
| A19 | **I_SHUNT1_CMP** | 9 | A2, B6, C9 | idem | **CMP1_HP0** |
| A21 | **I_SHUNT2_MES** | 24 | A9, B4, C8 | idem | — (chemin filtré) |
| A22 | **I_SHUNT2_CMP** | 25 | A10, B1, C10 | idem | **CMP2_HP3** |
| A23 | VREF_ADC | 16 | VREFHI | VREFHI | — |
| A24 | VREFLO_SENSE | 17 | VREFLO | VREFLO | — |

A11, A12, A14, A15, A16 sont libres — cinq voies de réserve, câblées jusqu'aux
réserves 1 à 5 de la nappe ADC-2.

### Voies shunt : deux chemins distincts

Le shield reprend chaque sortie d'AMC0300R deux fois.

- **Chemin protection** (A19, A22) : direct, sans filtre, Rs ≤ 50 Ω.
  → `CMPSS1` et `CMPSS2`, seuil par DAC 12 bits interne sur l'entrée négative,
  filtre numérique CMPSS, sortie vers la Trip Zone de l'ePWM. **Aucune broche
  externe pour le seuil.**
- **Chemin mesure** (A18, A21) : filtré anti-repliement, converti par l'ADC.

Un défaut sur le filtre ne désarme pas la protection, et le filtre ne retarde pas
le déclenchement.

### Blanking

Trois niveaux, aucun ne demande de broche :
1. filtre numérique du CMPSS (`CTRIPxFILCTL`, échantillonnage + seuil de vote) ;
2. fenêtre de blanking du sous-module Digital Compare de l'ePWM, synchronisée sur
   le compteur — c'est le mécanisme adapté au masquage du pic de commutation ;
3. CLB, pour une logique non standard.

### Contrainte d'acquisition

| Paramètre | Valeur (SPRSP61C) |
|---|---|
| Fenêtre d'acquisition minimale | **75 ns avec Rs ≤ 50 Ω** (90 ns sur broche AGPIO) |
| Capacité d'échantillonnage | ≈ 12,5 pF |
| Débit max | 4 MSPS à 120 MHz |
| VREFHI externe | 2,4 V à VDDA, typiquement 2,5 ou 3,0 V |
| VREFHI − VREFLO | ≥ 2,4 V |

`ACQPS` doit être ajusté à l'impédance de source réelle du shield, filtres
compris. Ne pas garder la valeur minimale par défaut sur les voies filtrées.

### CLB

Aucune broche dédiée. Entrées par le **CLB Input X-BAR** depuis n'importe quel
GPIO0-31, sorties par le **CLB Output X-BAR** sur B28 et B29. Les sorties CMPSS
passent par l'**Output X-BAR** vers B26 et B27 ; un seul OUTPUTXBAR peut agréger
plusieurs sources CMPSS.

---

## 5. Boot et mise à jour firmware

### Broches de sélection

Par défaut, **GPIO24 (BMSP1) et GPIO32 (BMSP0)** sur les deux MCU :

| Mode | GPIO24 | GPIO32 |
|---|---|---|
| Parallel IO | 0 | 0 |
| SCI / Wait Boot | 0 | 1 |
| CAN | 1 | 0 |
| **Flash** | **1** | **1** |

**Configuration retenue — une seule BMSP**, à programmer dans
`Z1_OTP_BOOTPIN_CONFIG` :

```
Key   = 0x5A   (bits 31:24)
BMSP2 = 0xFF   (désactivée)
BMSP1 = 0x18   (GPIO24)
BMSP0 = 0xFF   (désactivée)
        → 0x5AFF18FF
```

GPIO32 est ainsi libéré. GPIO24 à 1 → Flash, à 0 → SCI Wait Boot.

**Tester avec `EMU_BOOTPIN_CONFIG` avant de brûler l'OTP.** L'OTP est
irréversible ; Z2 est prioritaire sur Z1 si une correction devient nécessaire.

Restrictions : GPIO36 et GPIO38 sont interdits comme BMSP. Sur F28P551, si
l'adresse d'entrée Flash n'est pas programmée, le mode Flash part en ITRAP.

### Boot SCI ROM

Option 0 par défaut, `BOOTDEF = 0x01` : **SCITXDA sur GPIO29, SCIRXDA sur
GPIO28** — exactement B15 et B16. Aucune broche supplémentaire.

C'est un *wait boot* : le composant attend indéfiniment un `'A'` ou `'a'` pour
verrouiller son autobaud. L'ESP32 n'a aucune contrainte de temps.

### Mise à jour retenue : FOTA avec recopie de banque

Variante du §4 de TIDUEY4E, pas le LFU sans reset.

Principe : le binaire est **toujours compilé pour la banque 1 et exécuté depuis
la banque 0**. Après programmation de la banque 1, le noyau Flash recopie vers la
banque 0 puis branche sur `c_int00`. Un seul fichier de link, aucune banque à
suivre côté hôte.

**Coût : environ une seconde pendant laquelle l'application ne tourne pas.**
Inacceptable en marche sur un boost 500 V.

**Séquence imposée** :
1. l'ESP32 demande l'arrêt du convertisseur ;
2. le C2000 rampe à zéro, coupe Stage1_EN / Stage2_EN / HV_EN, active Discharge ;
3. le C2000 confirme la décharge et l'autorisation de mise à jour ;
4. l'ESP32 lance le transfert ;
5. recopie de banque, redémarrage, ré-initialisation complète depuis `main()`.

L'OLED reste piloté par l'ESP32 pendant toute l'opération et doit afficher la
progression — le C2000 est arrêté.

### Protocole côté ESP32

À réimplémenter d'après le `serial_flash_programmer` de C2000Ware :
verrouillage autobaud par `'A'`, identifiant de commande `0x700` pour le Live
DFU, puis transfert bloc par bloc avec vérification du checksum retourné par la
cible.

L'exemple TI tourne à 9600 baud, ce qui donne plusieurs minutes pour une image de
256 Ko. **Monter le débit** — limite exacte de l'autobaud `à vérifier`.

### Chemin de récupération

Si la recopie banque 1 → banque 0 est interrompue, la banque 0 est corrompue.
L'ESP32 met alors **BOOT_SEL (B4) à 0**, impulse **nRESET (B3)**, et le
bootloader ROM répond sur les mêmes GPIO29 / GPIO28.

`nRESET` doit être attaqué **en drain ouvert uniquement** : le MCU tire lui-même
cette ligne à zéro sur watchdog et sur brownout.

### Repli natif

Si le transfert échoue avant la recopie, le champ VERSION de la banque partielle
n'est pas mis à jour et la logique de sélection repart sur l'ancienne
application au reset suivant.

---

## 6. Rôles UART

**B15 / B16 portent trois usages sur les mêmes fils.** Le firmware C2000 doit les
multiplexer proprement :

1. **télémétrie** vers l'ESP32 en fonctionnement normal — le C2000 pousse ses
   grandeurs, l'ESP32 les affiche sur l'OLED et les publie en Wi-Fi ;
2. **commande FOTA** — l'ESP32 envoie l'identifiant `0x700`, traité dans
   l'interruption de réception SCI puis dans la boucle de fond ;
3. **boot ROM** en récupération, après BOOT_SEL + nRESET.

Contrainte connue : **SFRA et l'hôte de mise à jour partagent le même SCI** et ne
sont pas cumulables sur un seul canal.

Priorités d'interruption : l'ISR de la boucle de régulation doit être déclarée
`#pragma INTERRUPT(nom, HPI)` — priorité haute, contexte rapide, non imbricable.
L'ISR de réception SCI reste en priorité basse, imbricable.

---

## 7. LED et diagnostic local

| | F280037CSPM | F28P551SG5PM |
|---|---|---|
| LED bleue | GPIO39 — broche 46 | GPIO20 — broche 27 |
| LED rouge | GPIO32 — broche 40 | GPIO21 — broche 28 |

**Le firmware doit détecter le composant à l'exécution** et adresser les bons
GPIO, ou être compilé en deux variantes. GPIO20 et GPIO21 sont des broches
analogiques sur F28P551 : écrire `GPIOHAMSEL` pour les utiliser en numérique.

Vérifier l'état au reset de GPIO39 sur F280037, pour que la LED ne s'allume pas
pendant le démarrage.

---

## 8. Répartition des responsabilités firmware

**TMS320 C2000** — boucle de régulation des deux étages boost, HRPWM, protection
par CMPSS et Trip Zone, acquisition des 16 voies ADC, séquence d'arrêt et de
décharge, télémétrie par SCI, gestion du FOTA côté cible.

**ESP32** — Wi-Fi, hôte FOTA, affichage OLED par SPI, supervision, journalisation,
pilotage de la séquence d'arrêt avant mise à jour, contrôle de BOOT_SEL et
nRESET en récupération.

**Frontière nette** : l'ESP32 n'a aucune responsabilité temps réel. Il ne doit
jamais pouvoir retarder la boucle de régulation ni la protection. Toute demande
venant de l'ESP32 est traitée dans la boucle de fond du C2000, jamais dans l'ISR.

---

## 9. Reste à vérifier

- Nombre de banques Flash sur le F280037CSPM et le F28P551SG5PM.
- Débit SCI maximal accepté par l'autobaud du bootloader.
- Matériel LFU dédié sur le F28P551 (documenté pour le F28003x : permutation de
  la table de vecteurs PIE, permutation de blocs RAM).
- Caractéristiques de sortie des AMC0311S et AMC0300R : impédance, pleine
  échelle, bande passante.
- Courant d'entrée du REFIN des AMC0300R.
- Choix de VREFHI externe : 2,5 V ou 3,0 V.
- Fréquence de découpage définitive, pour dimensionner filtres, fenêtre de
  blanking et `ACQPS`.
- Attribution définitive de Stage1_EN, Stage2_EN, HV_EN et Discharge parmi les
  lignes disponibles de la rangée B.

---

## 10. Fichiers du projet

| Fichier | Contenu |
|---|---|
| `brochage-definitif.md` | brochage complet, nappes, alimentation |
| `boot-et-lfu.md` | modes de démarrage, BOOTPIN_CONFIG, LFU/FOTA |
| `trois-cartes.md` | justification de l'architecture |
| `brochage_F280037_PM64.csv` | brochage exhaustif extrait de SPRSP61C |
| `brochage_F28P551_PM64.csv` | brochage exhaustif extrait de SPRSPC5 |
| `kicad_c2000/` | symboles KiCad et table de correspondance |
