# Comment l'IA annonce

Analyse des annonces de l'IA de la Coinche à 4 (le réseau PPO `models/coinche_4p.pt`, qui joue Yoni et Noa sur le site). Le réseau n'a pas de règles écrites : on l'a fait annoncer sur **toutes les mains possibles** (10 518 300) et on a regardé ce qu'il choisit. Ses annonces sont les mêmes en « IA » et en « IA + recherche » : la recherche ne sert qu'au jeu de la carte.

## La fiche de l'IA

### Quand elle parle la première

| Annonce | Part des mains | Main typique (dans la couleur annoncée) |
|---|---|---|
| Passe | 29 % | moins de 3 atouts avec le Valet ou le 9 |
| **80** | 45 % | 3 atouts ou plus avec le Valet ou le 9 |
| 90 | 13 % | un peu plus fort : 3,4 atouts en moyenne, souvent le Valet |
| 100 – 110 | 12 % | Valet + 9 avec 4 atouts ou plus (le plus souvent **110**) |
| 120 et plus | 1 % | Valet + 9 avec environ 5 atouts, souvent la belote |

- Le **niveau** dépend des atouts (longueur, Valet + 9), pas des As : elle a en moyenne 0,7 As hors atout à tous les niveaux.
- Les **As** décident surtout *si* elle ouvre avec une main limite : avec le 9 sans le Valet et 3 atouts, elle ouvre 38 % du temps sans As, 97 % avec trois.
- Elle annonce sa meilleure couleur (le plus de majeures, puis le plus d'atouts) dans 86 % des cas.

### Quand son partenaire a ouvert (l'adversaire a passé)

Réponses dans la couleur du partenaire :

- **sur 80** : +30 avec Valet + 9 et 4 atouts ou plus ; +10 avec Valet + 9 et 3 atouts (+30 dès 2 As) ; +10 avec le Valet ou le 9 et 3 atouts ou plus ; avec 2 atouts, +10 de plus en plus souvent avec les As ;
- **sur 90** : +20 avec Valet + 9 et 4 atouts ou plus ; +10 avec Valet + 9 et 3 atouts (+20 avec 2 As) ; +10 avec le Valet et 3 atouts ou plus ; avec le 9 seul, rarement ;
- **sur 100** : toujours +10 quand elle répond, surtout avec Valet + 9 ou le Valet et 3 atouts ;
- **sur 110 et 120** : elle passe presque toujours, sauf avec Valet + 9 et 4 atouts ou plus (une fois sur deux).

| Ouverture du partenaire | Elle passe | Elle répond dans sa couleur | Elle annonce une autre couleur |
|---|---|---|---|
| 80 | 38 % | 33 % | 29 % |
| 90 | 61 % | 20 % | 19 % |
| 100 | 80 % | 12 % | 8 % |
| 110 | 92 % | 5 % | 3 % |
| 120 | 95 % | 3 % | 2 % |

- Pas de « +10 par As » comme Ruben (AsR) ou Claude (Petit jeu) : la **taille du saut** dépend de ses atouts, les **As** l'aident seulement à se décider à répondre.
- Sans Valet ni 9 dans la couleur du partenaire, elle annonce souvent sa propre couleur (une contre-proposition, pas une réponse).

Ces règles sont des **tendances** : chaque case des rapports donne la part exacte des mains où elle s'applique.

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `toutes_ouvertures.py` | passe les 10 518 300 mains dans le réseau quand l'IA parle la première |
| `toutes_reponses.py` | la même chose pour ses réponses aux 20 ouvertures possibles du partenaire (80 à 120 × 4 couleurs) |
| `echantillon.py` | première analyse sur des donnes tirées au hasard, et surtout le test d'une main précise |
| `types_de_mains.py` | pour chaque ouverture (80, 90…), la part de chaque type de main (ex. « 13 % des 80 sont des V + 2 atouts + 1 As ») |
| `rapports/types_ouvertures.md` | ces parts, annonce par annonce |
| `rapports/ouvertures.md` | tous les tableaux des ouvertures (résultats exacts) |
| `rapports/reponses.md` | tous les tableaux des réponses (résultats exacts) |
| `rapports/echantillon.md` | le rapport de la première analyse (échantillon) |
| `donnees/` | les choix de l'IA pour chaque main (≈ 65 Mo, **non versionné** : on le recrée avec `--calcul`) |

## Commandes

À lancer depuis la racine du dépôt :

```bash
python -m analyse_ia.toutes_ouvertures --calcul      # ≈ 1 minute, puis le rapport
python -m analyse_ia.toutes_reponses --calcul        # ≈ 10 minutes, puis le rapport
python -m analyse_ia.types_de_mains                  # quelles mains derrière chaque ouverture
python -m analyse_ia.echantillon --main "VP 9P AP 7P AC 10C RK 8T"
python -m analyse_ia.echantillon --main "9P 8P AC AK 10K RT DT 7T" --apres 90P
```

Cartes : valeur (7 8 9 10 V D R A) puis couleur (P pique, C cœur, K carreau, T trèfle). Sans `--calcul`, les deux premiers scripts refont seulement le rapport à partir de `donnees/`.
