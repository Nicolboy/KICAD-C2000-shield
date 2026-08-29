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

# Projet — shield d'isolation C2000, connecteur 2 × 24

## Ce qui fait autorité

`connecteur-2x24.md` **est** la source de vérité du brochage. Tout le reste en
découle par génération.

- Ne jamais éditer `build/*.kicad_sym` à la main. Modifier le `.md`, relancer
  `python3 connecteur_gen.py connecteur-2x24.md -o build/`.
- Si le symbole et le `.md` divergent, le `.md` a raison.

## Vérification avant tout commit

```
python3 connecteur_gen.py connecteur-2x24.md --check   # doit sortir en 0
kicad-cli sch erc --exit-code-violations projet.kicad_sch
kicad-cli pcb drc --exit-code-violations projet.kicad_pcb
```

## Décisions de conception à ne pas défaire

Ces choix ont l'air d'inefficacités et n'en sont pas. Ne pas les « optimiser »
sans décision explicite de ma part.

1. **B10 à B13 en GPIO génériques.** En mux 1 ce sont `EPWM3_A/B` et
   `EPWM4_A/B` — deux paires HRPWM complémentaires de réserve, gratuites. Les
   renommer en PWM détruit le double usage et fait perdre les quatre commandes
   du shield (Stage1_EN, Stage2_EN, HV_EN, Discharge).
2. **Masse isolante de part et d'autre de I_SHUNT1, I_SHUNT2 et VREF_ADC.**
   Non négociable, c'est de la mesure de courant.
3. **11 voies ADC pour 7 nécessaires.** La marge est volontaire.
4. **nRESET en drain ouvert uniquement.** Le MCU tire lui-même la ligne à zéro
   sur watchdog et brownout. Jamais de sortie push-pull côté shield.
5. **Point de jonction VSS/VSSA unique**, près du boîtier, une seule masse au
   connecteur.

## Deux variantes de PCB

F280037 et F28P551 partagent le connecteur (48 positions sur 48) mais divergent
sur : LED bleue et rouge, VDDIO broche 28, VDD broche 27, VREGENZ broche 46.
Toute divergence hors de cette liste est une erreur.

## Points ouverts — ne pas inventer de valeur

- Broches de mode de démarrage des deux MCU : à lire dans le manuel technique.
- VREFHI en mode externe : plage, impédance de source, courant.
- Courant de sortie GPIO : le mode 20 mA du F28P551 n'est pas confirmé dans
  SPRSPC5. Considérer 4 mA. Les DPC817 à 5 mA imposent un buffer côté shield.
- État au reset de GPIO39 (LED, PCB F280037).

Si une de ces valeurs est nécessaire, demander — ne pas combler par une
estimation plausible.
