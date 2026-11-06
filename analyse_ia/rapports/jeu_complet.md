# Comment l'IA joue : enchères disputées, contrats et jeu de la carte

Le réseau (`models/coinche_4p.pt`, coup le plus probable) joue les 4 places sur 149 015 donnes tirées au hasard ; 2 999 273 coups de la carte où il avait le choix, 1 190 512 annonces. Chaque case : la part des cas (sur « cas » situations). On ne compte que les coups où elle avait le choix. Place dans le pli : 0 = elle entame, 1 = elle joue en 2e, 2 = en 3e, 3 = en dernier.

## 1. Les contrats qu'elle prend

| contrat | cas | réussi | chuté |
|---|---|---|---|
| 80 | 8717 | 66 % | 34 % |
| 90 | 18033 | 65 % | 35 % |
| 100 | 26844 | 66 % | 34 % |
| 110 | 42624 | 64 % | 36 % |
| 120 | 30095 | 62 % | 38 % |
| 130 | 18792 | 55 % | 45 % |
| 140 | 3555 | 58 % | 42 % |
| 150 | 242 | 37 % | 63 % |
| 160 | 101 | 13 % | 87 % |

Réussite selon ce que le preneur a à l'atout :

| atout du preneur | cas | part |
|---|---|---|
| V+9, 4 atouts ou + | 24873 | 72 % |
| V+9, 3 atouts | 17542 | 63 % |
| V+9 seuls | 3908 | 59 % |
| V sans 9, 3 atouts ou + | 46557 | 62 % |
| 9 sans V, 3 atouts ou + | 21582 | 62 % |
| V ou 9, 2 atouts | 13246 | 56 % |
| V ou 9 sec | 2021 | 60 % |
| ni V ni 9 | 19286 | 59 % |

Réussite selon les atouts de l'équipe qui prend (preneur + partenaire) :

| atouts de l'équipe | cas | part |
|---|---|---|
| 1 | 50 | 2 % |
| 2 | 779 | 16 % |
| 3 | 8150 | 33 % |
| 4 | 33323 | 51 % |
| 5 | 55724 | 65 % |
| 6 | 39506 | 73 % |
| 7 | 10679 | 78 % |
| 8 | 797 | 81 % |

Points faits par l'attaque, en moyenne, selon le contrat :

| contrat | cas | points de l'attaque (moyenne) | marge moyenne |
|---|---|---|---|
| 80 | 8717 | 90 | +10 |
| 90 | 18033 | 98 | +8 |
| 100 | 26844 | 106 | +6 |
| 110 | 42624 | 113 | +3 |
| 120 | 30095 | 119 | -1 |
| 130 | 18792 | 123 | -7 |
| 140 | 3555 | 130 | -10 |
| 150 | 242 | 113 | -37 |
| 160 | 101 | 90 | -70 |

Coinches : 33 % des contrats ; l'attaque coinchée réussit 41 % du temps (sur 48722 coinches). Surcoinches : 1264. Contrats disputés (les deux équipes ont annoncé) : 77 %.

Réussite des contrats coinchés, selon le contrat :

| contrat coinché | cas | part |
|---|---|---|
| 80 | 2362 | 34 % |
| 90 | 4354 | 34 % |
| 100 | 5416 | 33 % |
| 110 | 12392 | 39 % |
| 120 | 11352 | 45 % |
| 130 | 10107 | 46 % |
| 140 | 2385 | 54 % |
| 150 | 241 | 37 % |
| 160 | 101 | 13 % |

## 2. Les enchères disputées

### Quand l'adversaire a ouvert (et que son équipe à elle n'a encore rien annoncé)

| contrat adverse | cas | surenchère | passe | coinche |
|---|---|---|---|---|
| 80 | 112755 | 60 % | 38 % | 2 % |
| 90 | 56654 | 49 % | 48 % | 2 % |
| 100 | 30265 | 39 % | 59 % | 2 % |
| 110 | 23110 | 30 % | 66 % | 4 % |
| 120 | 4356 | 23 % | 69 % | 7 % |

Selon sa meilleure couleur à elle (sur 80 à 100 adverses) :

| sa meilleure couleur | cas | surenchère | passe | coinche |
|---|---|---|---|---|
| 9 sans V, 3 atouts ou + | 53591 | 42 % | 55 % | 3 % |
| V ou 9 sec | 6218 | 17 % | 82 % | 1 % |
| V ou 9, 2 atouts | 39649 | 21 % | 79 % | 1 % |
| V sans 9, 3 atouts ou + | 47204 | 81 % | 17 % | 3 % |
| V+9 seuls | 8465 | 73 % | 25 % | 2 % |
| V+9, 3 atouts | 16103 | 95 % | 1 % | 4 % |
| V+9, 4 atouts ou + | 12946 | 99 % | 0 % | 1 % |
| ni V ni 9 | 15498 | 19 % | 80 % | 1 % |

### Quand elle coinche

Part de coinche selon ce qu'elle a dans l'atout du contrat adverse (adversaire à 80-100) :

| dans l'atout adverse | cas | part |
|---|---|---|
| V+9, 3 atouts | 633 | 88 % |
| V+9 seuls | 710 | 17 % |
| V sans 9, 3 atouts ou + | 3283 | 40 % |
| 9 sans V, 3 atouts ou + | 8870 | 17 % |
| V ou 9, 2 atouts | 22607 | 0 % |
| V ou 9 sec | 14713 | 0 % |
| ni V ni 9 | 148695 | 0 % |

… selon ses As hors de l'atout adverse :

| As hors atout | cas | part |
|---|---|---|
| 0 | 79738 | 2 % |
| 1 | 89699 | 2 % |
| 2 | 27785 | 2 % |
| 3 | 2452 | 2 % |

… selon le nombre d'atouts adverses qu'elle tient :

| (contrat, atouts adverses en main) | cas | part |
|---|---|---|
| 80 · 0 | 13152 | 0 % |
| 80 · 1 | 41241 | 0 % |
| 80 · 2 | 40214 | 0 % |
| 80 · 3 | 15563 | 6 % |
| 80 · 4 | 2585 | 52 % |
| 90 · 0 | 7503 | 0 % |
| 90 · 1 | 22308 | 0 % |
| 90 · 2 | 19632 | 1 % |
| 90 · 3 | 6406 | 11 % |
| 90 · 4 | 805 | 62 % |
| 100 · 0 | 4565 | 0 % |
| 100 · 1 | 12475 | 0 % |
| 100 · 2 | 10041 | 1 % |
| 100 · 3 | 2897 | 10 % |
| 100 · 4 | 287 | 68 % |
| 110 · 0 | 4640 | 1 % |
| 110 · 1 | 10149 | 1 % |
| 110 · 2 | 6633 | 4 % |
| 110 · 3 | 1553 | 29 % |
| 120 · 0 | 995 | 2 % |
| 120 · 1 | 1959 | 2 % |
| 120 · 2 | 1144 | 8 % |
| 120 · 3 | 241 | 62 % |

Main typique quand elle coinche (48722 coinches) :

| dans l'atout adverse | part des coinches |
|---|---|
| ni V ni 9 | 48 % |
| V ou 9, 2 atouts | 18 % |
| 9 sans V, 3 atouts ou + | 18 % |
| V sans 9, 3 atouts ou + | 7 % |
| V ou 9 sec | 4 % |
| V+9, 3 atouts | 2 % |
| V+9 seuls | 1 % |
| V+9, 4 atouts ou + | 1 % |

| As hors atout adverse | part des coinches |
|---|---|
| 0 | 35 % |
| 1 | 46 % |
| 2 | 17 % |
| 3 | 2 % |

### Quand son équipe est coinchée

| (qui a pris, atout) | cas | part |
|---|---|---|
| moi · 9 sans V, 3 atouts ou + | 11492 | 2 % |
| moi · V ou 9 sec | 896 | 0 % |
| moi · V ou 9, 2 atouts | 4512 | 0 % |
| moi · V sans 9, 3 atouts ou + | 15576 | 2 % |
| moi · V+9 seuls | 1938 | 1 % |
| moi · V+9, 3 atouts | 5072 | 1 % |
| moi · V+9, 4 atouts ou + | 6830 | 9 % |
| moi · ni V ni 9 | 2403 | 1 % |
| partenaire · 9 sans V, 3 atouts ou + | 2804 | 0 % |
| partenaire · V ou 9 sec | 2188 | 0 % |
| partenaire · V ou 9, 2 atouts | 4234 | 0 % |
| partenaire · V sans 9, 3 atouts ou + | 2769 | 0 % |
| partenaire · V+9 seuls | 528 | 0 % |
| partenaire · V+9, 3 atouts | 630 | 0 % |
| partenaire · V+9, 4 atouts ou + | 232 | 0 % |
| partenaire · ni V ni 9 | 34865 | 0 % |

### Quand l'adversaire surenchérit sur son équipe

Son équipe a un contrat, l'adversaire a annoncé par-dessus : elle relance, passe ou coinche ?

| contrat adverse | cas | passe | surenchère | coinche |
|---|---|---|---|---|
| 90 | 63421 | 39 % | 56 % | 5 % |
| 100 | 90671 | 49 % | 45 % | 5 % |
| 110 | 112482 | 59 % | 31 % | 10 % |
| 120 | 80010 | 61 % | 25 % | 14 % |
| 130 | 37567 | 64 % | 9 % | 27 % |
| 140 | 5958 | 59 % | 1 % | 40 % |
| 150 | 242 | 3 % | 1 % | 95 % |

## 3. L'entame du premier pli

| qui entame | cas | Roi/Dame/Valet | petite | atout | As | 10 |
|---|---|---|---|---|---|---|
| défense | 76260 | 35 % | 32 % | 14 % | 15 % | 3 % |
| partenaire du preneur | 34767 | 38 % | 32 % | 28 % | 3 % | 0 % |
| preneur | 37988 | 25 % | 21 % | 52 % | 1 % | 0 % |

La couleur entamée par la défense, selon qui l'a annoncée :

|  | cas | personne | partenaire | contrat | adversaires |
|---|---|---|---|---|---|
| défense | 76260 | 43 % | 40 % | 14 % | 3 % |

Défense : entame-t-elle sa couleur la plus courte (hors atout) ?

| carte entamée | cas | part |
|---|---|---|
| As | 11675 | 25 % |
| autre | 54048 | 34 % |

Défense : quand elle entame une couleur sans As, avec quelle carte ?

| longueur | cas | 7 | V | R | 8 | D | 9 | 10 |
|---|---|---|---|---|---|---|---|---|
| 1 carte(s) | 4976 | 27 % | 24 % | 21 % | 12 % | 12 % | 1 % | 3 % |
| 2 carte(s) | 17019 | 29 % | 22 % | 20 % | 13 % | 10 % | 2 % | 3 % |
| 3 carte(s) | 16692 | 31 % | 23 % | 19 % | 12 % | 9 % | 4 % | 3 % |
| 4 carte(s) | 5611 | 34 % | 23 % | 15 % | 11 % | 6 % | 5 % | 5 % |
| 5 carte(s) | 522 | 38 % | 26 % | 10 % | 7 % | 7 % | 5 % | 7 % |

## 4. L'attaque et ses atouts

Quand le preneur (ou son partenaire) entame, joue-t-il atout ? Selon les atouts encore dehors :

| (qui, atouts adverses restants) | cas | autre | atout |
|---|---|---|---|
| partenaire du preneur · 0 | 6387 | 73 % | 27 % |
| partenaire du preneur · 1 | 13355 | 70 % | 30 % |
| partenaire du preneur · 2 | 20966 | 69 % | 31 % |
| partenaire du preneur · 3 | 21217 | 75 % | 25 % |
| partenaire du preneur · 4 | 14160 | 60 % | 40 % |
| partenaire du preneur · 5 | 21697 | 57 % | 43 % |
| partenaire du preneur · 6 | 26544 | 70 % | 30 % |
| partenaire du preneur · 7 | 21114 | 84 % | 16 % |
| preneur · 0 | 54451 | 64 % | 36 % |
| preneur · 1 | 59540 | 61 % | 39 % |
| preneur · 2 | 63851 | 63 % | 37 % |
| preneur · 3 | 44542 | 58 % | 42 % |
| preneur · 4 | 52032 | 48 % | 52 % |
| preneur · 5 | 45365 | 55 % | 45 % |
| preneur · 6 | 14178 | 64 % | 36 % |
| preneur · 7 | 1262 | 70 % | 30 % |

… selon qu'il a l'atout maître :

| situation | cas | part |
|---|---|---|
| partenaire du preneur · atout maître · dehors | 37407 | 37 % |
| partenaire du preneur · atout maître · plus d'atout dehors | 6387 | 27 % |
| partenaire du preneur · pas maître · dehors | 101646 | 28 % |
| preneur · atout maître · dehors | 171592 | 44 % |
| preneur · atout maître · plus d'atout dehors | 54451 | 36 % |
| preneur · pas maître · dehors | 109178 | 38 % |

Quand l'attaque entame atout, avec quelle carte ?

| qui | cas | V | 7 | R | 8 | 9 | D | A | 10 |
|---|---|---|---|---|---|---|---|---|---|
| partenaire du preneur | 43919 | 18 % | 26 % | 14 % | 19 % | 5 % | 9 % | 5 % | 5 % |
| preneur | 137589 | 29 % | 15 % | 15 % | 12 % | 12 % | 10 % | 4 % | 4 % |

La défense entame-t-elle atout ?

| pli (0 = premier) | cas | part |
|---|---|---|
| 0 | 64393 | 16 % |
| 1 | 49276 | 16 % |
| 2 | 42092 | 17 % |
| 3 | 34053 | 18 % |
| 4 | 26180 | 21 % |
| 5 | 19014 | 24 % |
| 6 | 10957 | 29 % |

## 5. Les entames en cours de donne

Quand elle a une carte maître hors atout, la joue-t-elle ?

| (camp, pli) | cas | part |
|---|---|---|
| attaque · 1 | 53622 | 5 % |
| attaque · 2 | 51875 | 7 % |
| attaque · 3 | 53004 | 11 % |
| attaque · 4 | 54521 | 14 % |
| attaque · 5 | 54979 | 33 % |
| attaque · 6 | 54154 | 61 % |
| défense · 1 | 37964 | 28 % |
| défense · 2 | 36770 | 26 % |
| défense · 3 | 34494 | 29 % |
| défense · 4 | 32312 | 29 % |
| défense · 5 | 29038 | 45 % |
| défense · 6 | 25374 | 66 % |

Entame d'une couleur annoncée :

| camp | cas | personne | partenaire | adversaires | son équipe |
|---|---|---|---|---|---|
| attaque | 373357 | 72 % | 0 % | 20 % | 7 % |
| défense | 301694 | 59 % | 37 % | 5 % | 0 % |

## 6. En cours de pli

### Son partenaire est maître du pli

Elle fournit la couleur demandée : met-elle des points (« charge ») ?

| (place dans le pli, camp) | cas | part |
|---|---|---|
| 2 · attaque | 502 | 46 % |
| 3 · attaque | 34107 | 49 % |
| 3 · défense | 32690 | 83 % |

Elle ne peut pas fournir : coupe-t-elle quand même (ce n'est pas obligé) ?

| (place, partenaire) | cas | part |
|---|---|---|
| 2 · partenaire maître | 5584 | 31 % |
| 2 · partenaire pas sûr | 47280 | 32 % |
| 3 · partenaire maître | 48941 | 32 % |

Elle défausse sur son partenaire : donne-t-elle des points (10 ou As) ?

| (place, partenaire) | cas | part |
|---|---|---|
| 2 · maître | 34239 | 23 % |
| 2 · pas sûr | 69484 | 24 % |
| 3 · maître | 59499 | 35 % |

### L'adversaire gagne le pli

Elle peut prendre le pli : le prend-elle ?

| (place, camp, couleur demandée) | cas | part |
|---|---|---|
| 1 · attaque · ne peut pas fournir | 65845 | 100 % |
| 1 · attaque · peut fournir | 113136 | 80 % |
| 1 · défense · ne peut pas fournir | 20004 | 100 % |
| 1 · défense · peut fournir | 161673 | 82 % |
| 2 · attaque · ne peut pas fournir | 34908 | 100 % |
| 2 · attaque · peut fournir | 55630 | 81 % |
| 2 · défense · ne peut pas fournir | 11926 | 100 % |
| 2 · défense · peut fournir | 39058 | 84 % |
| 3 · attaque · ne peut pas fournir | 39418 | 100 % |
| 3 · attaque · peut fournir | 34146 | 83 % |
| 3 · défense · ne peut pas fournir | 11108 | 100 % |
| 3 · défense · peut fournir | 46686 | 83 % |

Quand elle prend en fournissant, avec sa plus haute carte ou juste ce qu'il faut ?

| place dans le pli | cas | part |
|---|---|---|
| 1 | 187465 | 58 % |
| 2 | 66501 | 77 % |
| 3 | 55318 | 80 % |

Elle ne prend pas en fournissant : met-elle sa plus petite carte ?

| place dans le pli | cas | part |
|---|---|---|
| 1 | 120922 | 73 % |
| 2 | 127242 | 64 % |
| 3 | 132371 | 64 % |

### Les défausses

Quand elle défausse (pas de la couleur demandée, pas d'atout joué) :

| pli | cas | couleur la plus courte | couleur la plus longue | autre |
|---|---|---|---|---|
| adversaire gagne | 396667 | 65 % | 34 % | 2 % |
| partenaire gagne | 217530 | 70 % | 29 % | 1 % |

Défausse dans une couleur où elle a l'As (« appel ») :

| pli | cas | part |
|---|---|---|
| adversaire gagne | 396667 | 14 % |
| partenaire gagne | 217530 | 13 % |

## 7. Là où la recherche corrige le réseau

Sur 645 682 coups (le réseau joue, la recherche dit ce qu'elle jouerait avec 20 mains imaginées), elle est d'accord 52 % du temps. « gain » : ce que la recherche pense gagner (en points de donne) en changeant de carte ; c'est une estimation bruitée, la médiane est plus sûre que la moyenne.

| (camp, pli) | coups | désaccord | gain moyen quand désaccord |
|---|---|---|---|
| attaque · 0 | 47592 | 62 % | 62.1 |
| attaque · 1 | 48195 | 64 % | 61.5 |
| attaque · 2 | 47026 | 62 % | 60.7 |
| attaque · 3 | 46643 | 58 % | 60.7 |
| attaque · 4 | 46095 | 50 % | 66.6 |
| attaque · 5 | 45993 | 35 % | 82.4 |
| attaque · 6 | 46875 | 13 % | 120.8 |
| défense · 0 | 48632 | 62 % | 59.3 |
| défense · 1 | 46831 | 59 % | 56.2 |
| défense · 2 | 46258 | 58 % | 53.8 |
| défense · 3 | 44765 | 54 % | 52.7 |
| défense · 4 | 43700 | 48 % | 55.1 |
| défense · 5 | 42682 | 31 % | 66.8 |
| défense · 6 | 44395 | 9 % | 98.7 |

Les corrections les plus fréquentes (ce que joue le réseau → ce que préfère la recherche) :

| place | le réseau joue | la recherche préfère | cas | gain moyen | gain médian |
|---|---|---|---|---|---|
| 0 | entame (figure) | entame (petite) | 12011 | 60.1 | 45.0 |
| 0 | entame (petite) | entame (figure) | 10879 | 57.1 | 43.5 |
| 0 | entame (petite) | entame maître (As) | 6382 | 82.6 | 64.0 |
| 0 | entame (figure) | entame maître (As) | 5976 | 79.1 | 63.0 |
| 2 | fournit qui ne prend pas (figure) | fournit qui ne prend pas (petite) | 3728 | 42.1 | 36.0 |
| 3 | fournit qui ne prend pas (figure) | fournit qui ne prend pas (petite) | 3709 | 39.0 | 30.0 |
| 1 | défausse qui ne prend pas (petite) | défausse qui ne prend pas (figure) | 3527 | 44.4 | 33.5 |
| 0 | entame atout (petite) | entame (petite) | 3464 | 75.1 | 61.0 |
| 0 | entame (petite) | entame (10) | 3224 | 65.5 | 50.8 |
| 0 | entame (petite) | entame atout (figure) | 3148 | 75.1 | 61.0 |
| 3 | défausse qui ne prend pas (petite) | défausse qui ne prend pas (figure) | 3093 | 49.5 | 36.0 |
| 0 | entame (figure) | entame (10) | 2974 | 64.1 | 48.0 |
| 0 | entame (figure) | entame atout (figure) | 2965 | 76.0 | 61.0 |
| 0 | entame atout (petite) | entame (figure) | 2874 | 73.5 | 54.5 |
| 2 | défausse qui ne prend pas (figure) | défausse qui ne prend pas (petite) | 2851 | 54.5 | 40.0 |
| 0 | entame (petite) | entame atout maître (V/9) | 2844 | 86.0 | 65.5 |
| 3 | fournit qui ne prend pas (petite) | fournit qui ne prend pas (figure) | 2745 | 34.6 | 25.5 |
| 2 | défausse qui ne prend pas (petite) | défausse qui ne prend pas (figure) | 2660 | 50.6 | 38.0 |
| 0 | entame (figure) | entame atout maître (V/9) | 2631 | 84.5 | 65.5 |
| 0 | entame (figure) | entame atout (petite) | 2431 | 70.0 | 57.5 |
| 0 | entame maître (As) | entame (figure) | 2422 | 56.3 | 42.0 |
| 0 | entame atout maître (V/9) | entame (petite) | 2412 | 69.0 | 48.5 |
| 0 | entame (petite) | entame maître (10) | 2378 | 76.0 | 48.0 |
| 0 | entame maître (As) | entame (petite) | 2367 | 59.1 | 42.0 |
| 0 | entame (petite) | entame atout (petite) | 2357 | 70.5 | 57.0 |
| 3 | défausse qui ne prend pas (figure) | défausse qui ne prend pas (petite) | 2315 | 53.4 | 39.0 |
| 1 | fournit qui ne prend pas (petite) | fournit qui prend (figure) | 2131 | 41.3 | 31.0 |
| 0 | entame (figure) | entame maître (10) | 2105 | 71.3 | 45.5 |
| 2 | fournit qui ne prend pas (petite) | fournit qui ne prend pas (figure) | 2092 | 37.0 | 28.0 |
| 0 | entame atout maître (V/9) | entame (figure) | 2059 | 71.5 | 50.0 |
| 1 | défausse qui ne prend pas (figure) | défausse qui ne prend pas (petite) | 2038 | 49.6 | 40.0 |
| 1 | fournit qui prend (figure) | fournit qui prend (10) | 1907 | 43.1 | 34.0 |
| 0 | entame atout (figure) | entame (petite) | 1903 | 81.2 | 63.0 |
| 1 | fournit qui ne prend pas (petite) | fournit qui prend (10) | 1653 | 51.7 | 40.0 |
| 1 | fournit qui ne prend pas (figure) | fournit qui ne prend pas (petite) | 1587 | 41.2 | 35.5 |
| 1 | fournit qui prend (figure) | fournit maître qui prend (As) | 1545 | 58.0 | 43.5 |

Par type de situation (désaccord et gain moyen) :

| (place, rôle, partenaire) | coups | désaccord | gain total par 1000 coups |
|---|---|---|---|
| 0 · défense · - | 89776 | 63 % | 41891 |
| 0 · partenaire du preneur · - | 49102 | 66 % | 44626 |
| 0 · preneur · - | 85724 | 60 % | 44729 |
| 1 · défense · - | 84623 | 44 % | 21589 |
| 1 · partenaire du preneur · - | 28643 | 42 % | 21801 |
| 1 · preneur · - | 24902 | 42 % | 25648 |
| 2 · défense · - | 35270 | 39 % | 18561 |
| 2 · défense · partenaire gagne | 21723 | 38 % | 23396 |
| 2 · partenaire du preneur · - | 22743 | 39 % | 20525 |
| 2 · partenaire du preneur · partenaire gagne | 32060 | 40 % | 22633 |
| 2 · preneur · - | 14566 | 42 % | 25617 |
| 2 · preneur · partenaire gagne | 15578 | 41 % | 28428 |
| 3 · défense · - | 63469 | 35 % | 18538 |
| 3 · défense · partenaire gagne | 22402 | 41 % | 24650 |
| 3 · partenaire du preneur · - | 11711 | 34 % | 19099 |
| 3 · partenaire du preneur · partenaire gagne | 15533 | 43 % | 23882 |
| 3 · preneur · - | 16932 | 35 % | 25716 |
| 3 · preneur · partenaire gagne | 10925 | 43 % | 36929 |
