# Méthode — concevoir une carte avec KiCad et un agent

Cette carte n'est pas dessinée à la souris du début à la fin. Le partage est le
suivant, et il n'est pas négociable au milieu d'une séance :

| | Qui |
|---|---|
| Lire les datasheets, en extraire les contraintes | **agent** |
| Écrire la spécification et le brochage en Markdown | **agent**, relu par toi |
| Générer les symboles, poser les composants, câbler par étiquettes | **agent** |
| Choisir les boîtiers et renseigner les empreintes | **agent** |
| Peupler le PCB depuis le schéma | **KiCad**, un raccourci |
| **Placement et routage** | **toi, à la main** |

Le routage reste manuel parce qu'il encode des choix — boucles de retour,
proximité des découplages, séparation analogique/numérique — qu'aucun script ne
devine et qu'un agent ne doit pas improviser sur une chaîne de mesure de
courant.

---

## La règle qui casse tout si on l'oublie

> **KiCad FERMÉ pour toucher un `.kicad_sch`. KiCad OUVERT pour toucher un
> `.kicad_pcb`.**

KiCad travaille sur une copie en mémoire et la réécrit intégralement à
l'enregistrement. Une modification faite sur le disque pendant ce temps est
**perdue sans le moindre message** : ni erreur, ni avertissement, le fichier
est simplement écrasé par la version d'avant.

C'est arrivé une fois dans ce projet. Le symptôme est déroutant : on corrige
quelque chose, on vérifie que c'est écrit, et la correction n'a aucun effet.

Les générateurs refusent maintenant de démarrer tant que le fichier verrou
`~<projet>.kicad_pro.lck` existe (`kicad_gen.refuser_si_kicad_ouvert`). La règle
est devenue exécutable plutôt que de reposer sur l'attention de qui que ce soit.

---

## Le déroulé d'une séance

```
1.  git commit            ← avant toute chose, c'est le seul vrai filet
2.  KiCad ferme
3.  python gen_*.py       ← symboles, composants, empreintes
4.  kicad-cli sch erc     ← doit charger ; les violations se lisent, pas se corrigent
5.  KiCad ouvert, PCB, F8 ← « Mettre a jour le PCB depuis le schema »
6.  placement + routage   ← a la main
7.  kicad-cli pcb drc
```

L'étape 1 n'est pas une politesse. Trois fois dans ce projet, un commit a permis
de revenir d'un fichier corrompu ou écrasé — plus souvent que n'importe quelle
règle de permission.

---

## Ce que `kicad-cli` sait et ne sait pas

**Sait** : `sch erc`, `pcb drc`, `sch export` (netlist, PDF, nomenclature),
`pcb export` (Gerber, perçage, position), `sch upgrade`, `pcb upgrade`.

**Ne sait pas** : mettre à jour un PCB depuis un schéma. Il n'y a **aucun**
équivalent en ligne de commande de F8. Il faut passer par l'interface, ou par
kipy sur l'instance ouverte.

**Piège de diagnostic** : quand un fichier est malformé, `kicad-cli` répond
`Échec du chargement de la schématique` et rien d'autre — pas de ligne, pas de
jeton fautif. La seule méthode qui marche est la bissection : réduire
l'insertion jusqu'au plus petit morceau qui casse, puis comparer ce morceau à un
équivalent que **KiCad a écrit lui-même**.

---

## Les pièges de format, et leur signature

Chacun a coûté du temps. Ils se reconnaissent vite une fois vus.

### Les sous-unités gardent le nom nu

Dans la section `(lib_symbols)` d'un schéma, le symbole de premier niveau porte
le préfixe de bibliothèque, **ses sous-unités non** :

```
(symbol "Connector:TC2050"        ← préfixé
  (symbol "TC2050_1_1"            ← NU, pas "Connector:TC2050_1_1"
```

Les préfixer aussi rend le fichier illisible. *Signature : échec du chargement,
sans plus.*

### Les variantes `(extends ...)` n'ont pas de broches

`MCP1700x-330xxTT` hérite de sa géométrie. Un bloc copié tel quel n'a pas une
seule broche. Il faut remonter la chaîne jusqu'à l'ancêtre, partir de **son**
bloc entier, et y reporter les propriétés de la variante — sinon le symbole posé
diffère de celui que KiCad recalcule. *Signature : `lib_symbol_mismatch`.*

### Tout doit tomber sur la grille de 1,27 mm

Une origine de placement à 40 mm n'est pas un multiple de 1,27. *Signature : un
`endpoint_off_grid` par composant posé.* Vaut aussi pour les symboles importés,
que `gen_devkit.py` recale pour cette raison.

### L'empreinte se lit sur l'instance, pas sur la bibliothèque

Au F8, KiCad lit la propriété `Footprint` de **l'instance**. Une bibliothèque
parfaitement renseignée ne suffit pas. *Signature :
`Ne peut ajouter le composant 'U1' (empreinte non assignée)`.*

Et les deux formats coexistent : KiCad 10 écrit une propriété `Footprint` vide
qu'il faut remplir, KiCad 8 n'en écrit aucune et il faut l'insérer.
`gen_empreintes.py` traite les deux, et lit `sym-lib-table` plutôt que le cache
`(lib_symbols)` du schéma — ce cache s'est révélé incomplet.

---

## Ce qui rend le câblage automatique possible

Les schémas de ce projet ne contiennent **aucun fil**. Toute la connectivité
passe par des étiquettes globales posées exactement sur le point de connexion de
chaque broche.

C'est ce qui permet à un script d'ajouter un composant sans rien router : il
pose le symbole, puis une étiquette par broche au nom du net. L'ordre n'a aucune
importance, et deux étiquettes de même nom sont reliées où qu'elles soient sur
la feuille.

Corollaire à ne pas oublier : **déplacer un symbole sans déplacer ses étiquettes
les détache toutes en silence**. L'ERC ne dit rien de plus, et la netlist se
vide. `gen_devkit.py` déplace les deux ensemble pour cette raison, et vérifie
que le compte d'étiquettes retrouvées est exact.

---

## Les outils du dépôt

| Script | Rôle |
|---|---|
| `gen_symbole_mcu.py` | symboles MCU carrés, corps dimensionné d'après les noms de broche |
| `gen_devkit.py` | monte les deux projets devkit depuis `src/` |
| `gen_composants.py` | pose les composants discrets et leurs étiquettes |
| `gen_leds.py` | réaffecte les LED sur d'autres broches |
| `gen_empreintes.py` | renseigne les empreintes manquantes sur les instances |
| `kicad_gen.py` | briques communes, dont le garde-fou de verrou |

Tous sont **idempotents** : relancés sur un fichier déjà traité, ils ne font
rien. On peut les enchaîner sans réfléchir à l'ordre.

---

## Lire les datasheets

Les PDF de TI s'extraient avec `pypdf` (installé dans le venv). Le texte sort
désordonné mais cherchable, ce qui suffit pour retrouver une table ou un
paragraphe, puis le lire dans son contexte.

Deux trouvailles de ce projet illustrent ce que ça rapporte, et qu'aucune des
deux n'était dans les documents de départ :

- SPRSPC5 §5.5 — les rappels internes des GPIO sont **désactivés pendant le
  boot**. Sans rappel externe sur les deux broches de sélection, le mode de
  démarrage est tiré au sort.
- SPRSPC5 §5.3 — « This device does not have a TRSTn pin », écrit deux fois. Ce
  qui a levé une inquiétude légitime sur le câblage du JTAG.

La règle qui va avec : **une valeur qu'on n'a pas lue ne s'invente pas.** Les
points ouverts sont listés en fin de `decisions.md` et attendent une lecture,
pas une estimation plausible.

---

## En cas de

| Symptôme | Cause probable |
|---|---|
| `Échec du chargement de la schématique` | s-expression malformée — bissecter, comparer à un bloc écrit par KiCad |
| Une correction n'a aucun effet | KiCad était ouvert et a réécrit le fichier |
| `empreinte non assignée` au F8 | propriété `Footprint` vide ou absente **sur l'instance** |
| `endpoint_off_grid` en rafale | coordonnées hors de la grille de 1,27 mm |
| `lib_symbol_mismatch` | cache de symbole périmé, ou héritage `(extends)` mal aplati |
| Netlist vide après un déplacement | étiquettes globales détachées de leurs broches |
| `power_pin_not_driven` | attendu — voir `decisions.md` §8, le `PWR_FLAG` |
