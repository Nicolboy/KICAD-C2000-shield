# KICAD-C2000-shield

Shield d'isolation et cartes devkit pour TMS320 C2000, conçus sous KiCad 10.
Le brochage est décrit en Markdown, les symboles et les projets KiCad en sont
**générés** — le document reste la source de vérité, pas le schéma.

Cible : une commande numérique de convertisseur de puissance isolé, pilotée par
un C2000 et supervisée par un ESP32-C6 pour le Wi-Fi et la mise à jour FOTA.

---

## Architecture — quatre cartes, une barrière

| Carte | Rôle |
|---|---|
| **Puissance** | Conversion, barrière d'isolation, isolateurs (AMC0311S, AMC0300R, ISO7710, DPC817), shunts en connexion Kelvin, régulateurs |
| **Shield** | Support mécanique des deux devkits, adaptation de brochage, conditionnement analogique, protections. **Aucun composant isolé** |
| **Devkit C2000** | MCU, deux LDO 3,3 V, JTAG, bouton reset, LED, cavalier de boot |
| **Devkit ESP32** | Wi-Fi, hôte FOTA, écran OLED en SPI |

L'isolation est entièrement confinée à la carte de puissance. Le shield ne fait
que du conditionnement côté froid : c'est ce qui permet de le fabriquer en
2 couches à la maison sans se poser de question de ligne de fuite.

Liaison shield ↔ puissance : quatre nappes 2 × 8 à **alternance signal / masse
stricte 1:1**, aucune alimentation dedans. Le +5 V passe par un connecteur
séparé — les 500 mA de la commande n'ont pas à partager leur retour avec les
masses de référence des voies ADC.

---

## Le point de conception le plus notable

**Le connecteur est identique à 100 % entre le F280037 et le F28P551**, 56
positions sur 56. Les deux devkits sont interchangeables sur le shield.

Ce n'est pas une coïncidence, c'est le résultat d'un arbitrage : les LED ont été
délibérément posées sur les **entrées/sorties non communes** aux deux boîtiers,
pour que toutes les broches qui traversent le connecteur, elles, soient
communes. Les quatre divergences restent locales à la carte devkit :

| Broche | F280037 | F28P551 |
|---|---|---|
| 27 | VDD 1,2 V | LED bleue (GPIO20) |
| 28 | VDDIO 3,3 V | LED rouge (GPIO21) |
| 40 | LED rouge (GPIO32) | pastille de test |
| 46 | LED bleue (GPIO39) | VREGENZ à VSS |

La cause profonde est le régulateur 1,2 V : le F28P551 a le sien en interne,
activé par VREGENZ à VSS ; le F280037 en 64 PM non-Q n'a pas cette broche et
demande un LDO supplémentaire.

---

## Le brochage est du code

Le fichier [`doc/spec-devkit.md`](doc/spec-devkit.md) fait autorité. Les
symboles KiCad, les schémas et les vérifications en découlent par génération —
on ne modifie jamais un `.kicad_sym` à la main.

```
doc/spec-devkit.md            source de vérité, relue par un humain
        │
        ├── gen_symbole_mcu.py   → build/C2000_MCU_LQFP64.kicad_sym
        │                          (dimensionne le symbole depuis les noms)
        │
        └── gen_devkit.py        → devkit_A_F280037.*  devkit_B_F28P551.*
              ▲                    kicad_gen.py — primitives communes
              │
            src/*.kicad_sch        schémas source des devkits, versionnés

shield.*                       édité à la main dans KiCad — pas généré
```

L'intérêt n'est pas le gain de temps, c'est que **les règles de conception
deviennent exécutables**. Les générateurs vérifient ce que le document promet :
unicité des broches et des GPIO, masse de part et d'autre des voies de mesure de
courant, présence des réserves. Une divergence entre l'intention et le schéma
est une erreur de script, pas un oubli qu'on découvre au routage.

`gen_symbole_mcu.py` dimensionne par exemple le corps du symbole à partir de la
longueur réelle du nom de broche le plus long, pour que les textes des quatre
faces ne se croisent jamais — plutôt qu'une taille choisie à l'œil qui casse au
premier nom un peu long.

---

## Projets KiCad

Trois, pas un de plus.

| Projet | Contenu |
|---|---|
| `shield.*` | Shield, connecteurs devkit 2 × 28, quatre nappes, ESP32-C6 |
| `devkit_A_F280037.*` | Devkit TMS320F280037CSPM |
| `devkit_B_F28P551.*` | Devkit TMS320F28P551SG5PM |

---

## Reproduire

KiCad 10 et Python 3.12 requis. `kicad-cli` doit être dans le `PATH`.

```bash
python gen_symbole_mcu.py -o build/     # symboles MCU
python gen_devkit.py --force            # les deux projets devkit

kicad-cli sch erc --exit-code-violations <projet>.kicad_sch
kicad-cli pcb drc --exit-code-violations <projet>.kicad_pcb
```

`shield.*` n'apparaît pas ici : il est édité à la main et ne se régénère pas.
Les schémas de devkit produits à la racine sont en revanche **jetables** — toute
retouche manuelle y est perdue au prochain `--force`. Ce qui doit survivre se
modifie dans `src/` ou dans le générateur.

Chaque carte existe en **deux versions de fabrication** : 2 couches gravées à
la maison — pistes 1 mm, vias 2 mm, perçage 0,8 mm — pour itérer vite sur la
mécanique, et 4 couches en fabrication externe, avec plan de masse continu sous
la zone analogique. Même schéma, même brochage, seul le PCB change.

---

## État d'avancement

Travail en cours, et le dire plutôt que de le masquer :

- **Schémas** — connecteurs posés, alimentations câblées avec `PWR_FLAG` par
  net. Le routage des signaux n'est pas fait : il demande des choix de
  conception qui n'ont pas leur place dans un générateur. D'où les
  `pin_not_connected` encore présents à l'ERC.
- **PCB** — non routés. Le DRC passe à 0 sur les trois projets, ce qui ne prouve
  rien tant qu'il n'y a pas de piste.
- **Carte de puissance** — spécifiée dans `doc/`, pas encore dessinée.

Les points laissés ouverts — caractéristiques de sortie des AMC, courant
d'entrée du REFIN, choix de VREFHI — sont listés en fin de
[`doc/decisions.md`](doc/decisions.md). Ils attendent une lecture de datasheet,
pas une estimation.

---

## Décisions à ne pas défaire

Certains choix ressemblent à des inefficacités sans en être. Les douze sont
documentés dans [`doc/decisions.md`](doc/decisions.md), chacun avec sa raison et
ce qui casse si on le défait — entre autres :

- Les **PWM3 et PWM4 restent en réserve et restent des PWM** : ce sont les deux
  seules paires complémentaires HRPWM avec temps mort matériel disponibles.
- Chaque shunt sort **deux fois**, `_MES` filtré et `_CMP` direct. Le chemin
  comparateur attaque le CMPSS sans filtre anti-repliement : pas de retard sur
  le déclenchement de la Trip Zone, et un défaut du filtre ne désarme pas la
  protection.
- Les **16 voies ADC sortent toutes** pour 9 nécessaires, les 5 libres étant
  câblées jusqu'aux réserves de nappe. Une voie ajoutée plus tard se raccorde
  sans retoucher une seule carte.

---

## Licence

[CERN-OHL-S v2](LICENSE) — CERN Open Hardware Licence, fortement réciproque.

Tu peux étudier, modifier, fabriquer et distribuer ce matériel. En contrepartie,
si tu distribues un produit fondé dessus, ou une version modifiée, tu dois
publier les sources correspondantes sous la même licence.

C'est la licence de référence du matériel libre, l'équivalent de la GPL côté
logiciel. Si tu préfères une réciprocité limitée à la carte elle-même, ou pas de
réciprocité du tout, les variantes CERN-OHL-W et CERN-OHL-P existent.
