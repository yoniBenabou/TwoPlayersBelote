# Comment l'IA annonce

Modèle : `C:\Users\yonib\TwoPlayersBelote\models\coinche_4p.pt`. Annonce retenue : la plus probable pour le réseau (comme dans le site).

## Ouvertures (l'IA parle la première, 20000 donnes)

| Annonce | Fréquence | Valet | 9 | Valet + 9 | As d'atout | Atouts (moy.) | As hors atout (moy.) | 10 hors atout (moy.) | Belote | Couleurs (moy.) |
|---|---|---|---|---|---|---|---|---|---|---|
| Passe (meilleure couleur) | 29 % | 29 % | 57 % | 2 % | 30 % | 2.5 | 0.6 | 0.7 | 2 % | 3.9 |
| 80 | 45 % | 63 % | 41 % | 16 % | 34 % | 3.1 | 0.7 | 0.6 | 13 % | 3.7 |
| 90 | 13 % | 75 % | 53 % | 34 % | 30 % | 3.4 | 0.7 | 0.6 | 18 % | 3.6 |
| 100 | 6 % | 89 % | 62 % | 54 % | 33 % | 3.8 | 0.7 | 0.6 | 21 % | 3.5 |
| 110 | 6 % | 92 % | 64 % | 57 % | 31 % | 4.2 | 0.6 | 0.4 | 37 % | 3.3 |
| 120 | 1 % | 93 % | 78 % | 71 % | 43 % | 4.8 | 0.7 | 0.4 | 51 % | 3.1 |
| 150 | 0 % | 100 % | 100 % | 100 % | 50 % | 6.0 | 0.0 | 0.5 | 50 % | 2.5 |
| 160 | 0 % | 0 % | 0 % | 0 % | 0 % | 0.0 | 1.0 | 0.0 | 0 % | 2.0 |

### Ce qu'elle ouvre selon sa main (meilleure couleur d'atout × As hors atout)

Chaque case : l'annonce la plus fréquente, sa part, et le nombre de donnes.

| Atout | 0 As | 1 As | 2 As | 3 As |
|---|---|---|---|---|
| V+9, 4 atouts ou + | **110** 35 % (872) | **110** 41 % (547) | **110** 58 % (84) | – |
| V+9, 3 atouts | **80** 53 % (911) | **80** 42 % (770) | **90** 34 % (195) | (peu de donnes : 12) |
| V+9 seuls | **80** 64 % (322) | **80** 74 % (379) | **80** 69 % (148) | (peu de donnes : 4) |
| V sans 9, 3 atouts ou + | **80** 58 % (2711) | **80** 61 % (2113) | **80** 55 % (478) | **80** 50 % (22) |
| 9 sans V, 3 atouts ou + | **80** 44 % (2598) | **80** 56 % (2121) | **80** 69 % (445) | **80** 89 % (28) |
| V ou 9, 2 atouts | **Passe** 80 % (1167) | **Passe** 65 % (1616) | **Passe** 51 % (506) | **80** 53 % (30) |
| V ou 9 sec | **Passe** 79 % (105) | **Passe** 75 % (245) | **Passe** 61 % (145) | **Passe** 58 % (19) |
| ni V ni 9 | **Passe** 69 % (620) | **Passe** 60 % (562) | **Passe** 54 % (204) | **Passe** 52 % (21) |

## Réponses (son partenaire ouvre, l'adversaire passe ; 6000 donnes par niveau)

Ce qu'elle a dans l'atout du partenaire × ses As hors atout. Chaque case : la réponse la plus fréquente (+10, +20… dans la couleur du partenaire, « autre » = une autre couleur), sa part, et le nombre de donnes.

### Sur 80 du partenaire

| Dans son atout | 0 As | 1 As | 2 As | 3 As |
|---|---|---|---|---|
| V+9, 4 atouts ou + | **+30** 60 % (81) | **+30** 69 % (35) | (peu : 4) | – |
| V+9, 3 atouts | **+10** 48 % (65) | **+10** 47 % (64) | **+10** 44 % (16) | – |
| V+9 seuls | **+10** 50 % (28) | **+10** 42 % (33) | (peu : 10) | (peu : 1) |
| V sans 9, 3 atouts ou + | **+10** 45 % (271) | **+10** 54 % (207) | **+10** 47 % (38) | (peu : 3) |
| 9 sans V, 3 atouts ou + | **+10** 46 % (269) | **+10** 54 % (183) | **+10** 59 % (27) | (peu : 1) |
| V ou 9, 2 atouts | **Passe** 43 % (374) | **+10** 41 % (409) | **+10** 55 % (93) | (peu : 9) |
| V ou 9 sec | **Passe** 52 % (131) | **Passe** 37 % (182) | **autre (90)** 36 % (76) | (peu : 5) |
| ni V ni 9 | **Passe** 51 % (1291) | **Passe** 44 % (1521) | **Passe** 38 % (521) | **Passe** 42 % (52) |

### Sur 90 du partenaire

| Dans son atout | 0 As | 1 As | 2 As | 3 As |
|---|---|---|---|---|
| V+9, 4 atouts ou + | **+20** 65 % (57) | **+20** 62 % (39) | (peu : 11) | – |
| V+9, 3 atouts | **+10** 66 % (74) | **+10** 51 % (81) | **+20** 47 % (17) | (peu : 3) |
| V+9 seuls | **+10** 34 % (32) | **+10** 53 % (36) | (peu : 5) | – |
| V sans 9, 3 atouts ou + | **+10** 43 % (250) | **+10** 50 % (217) | **+10** 58 % (48) | (peu : 3) |
| 9 sans V, 3 atouts ou + | **Passe** 58 % (252) | **Passe** 53 % (203) | **+10** 42 % (38) | (peu : 6) |
| V ou 9, 2 atouts | **Passe** 84 % (346) | **Passe** 71 % (413) | **Passe** 59 % (145) | (peu : 9) |
| V ou 9 sec | **Passe** 67 % (144) | **Passe** 72 % (200) | **Passe** 65 % (78) | (peu : 3) |
| ni V ni 9 | **Passe** 69 % (1248) | **Passe** 68 % (1526) | **Passe** 67 % (455) | **Passe** 46 % (61) |

### Sur 100 du partenaire

| Dans son atout | 0 As | 1 As | 2 As | 3 As |
|---|---|---|---|---|
| V+9, 4 atouts ou + | **+10** 62 % (65) | **+10** 71 % (48) | (peu : 8) | – |
| V+9, 3 atouts | **+10** 69 % (67) | **+10** 69 % (55) | **+10** 81 % (16) | (peu : 1) |
| V+9 seuls | **Passe** 86 % (35) | **Passe** 62 % (29) | (peu : 11) | – |
| V sans 9, 3 atouts ou + | **Passe** 55 % (256) | **+10** 51 % (207) | **+10** 70 % (40) | (peu : 3) |
| 9 sans V, 3 atouts ou + | **Passe** 81 % (253) | **Passe** 69 % (227) | **+10** 56 % (39) | (peu : 1) |
| V ou 9, 2 atouts | **Passe** 95 % (382) | **Passe** 93 % (423) | **Passe** 80 % (136) | (peu : 6) |
| V ou 9 sec | **Passe** 92 % (143) | **Passe** 90 % (193) | **Passe** 88 % (84) | (peu : 8) |
| ni V ni 9 | **Passe** 87 % (1203) | **Passe** 84 % (1540) | **Passe** 81 % (479) | **Passe** 86 % (42) |

### Sur 110 du partenaire

| Dans son atout | 0 As | 1 As | 2 As | 3 As |
|---|---|---|---|---|
| V+9, 4 atouts ou + | **+10** 40 % (63) | **+10** 53 % (49) | (peu : 5) | – |
| V+9, 3 atouts | **Passe** 86 % (64) | **Passe** 58 % (60) | **Passe** 47 % (19) | – |
| V+9 seuls | **Passe** 100 % (34) | **Passe** 95 % (37) | (peu : 7) | – |
| V sans 9, 3 atouts ou + | **Passe** 89 % (263) | **Passe** 76 % (210) | **Passe** 79 % (34) | (peu : 1) |
| 9 sans V, 3 atouts ou + | **Passe** 95 % (265) | **Passe** 88 % (196) | **Passe** 98 % (49) | (peu : 1) |
| V ou 9, 2 atouts | **Passe** 99 % (359) | **Passe** 99 % (409) | **Passe** 99 % (111) | (peu : 14) |
| V ou 9 sec | **Passe** 97 % (145) | **Passe** 98 % (178) | **Passe** 99 % (73) | (peu : 6) |
| ni V ni 9 | **Passe** 95 % (1231) | **Passe** 95 % (1553) | **Passe** 93 % (519) | **Passe** 91 % (45) |

### Sur 120 du partenaire

| Dans son atout | 0 As | 1 As | 2 As | 3 As |
|---|---|---|---|---|
| V+9, 4 atouts ou + | **Passe** 36 % (61) | **+10** 37 % (43) | (peu : 5) | – |
| V+9, 3 atouts | **Passe** 97 % (61) | **Passe** 80 % (66) | **Passe** 47 % (19) | (peu : 1) |
| V+9 seuls | **Passe** 100 % (34) | **Passe** 100 % (42) | **Passe** 100 % (19) | – |
| V sans 9, 3 atouts ou + | **Passe** 87 % (254) | **Passe** 89 % (209) | **Passe** 80 % (50) | (peu : 1) |
| 9 sans V, 3 atouts ou + | **Passe** 94 % (252) | **Passe** 94 % (215) | **Passe** 89 % (36) | (peu : 2) |
| V ou 9, 2 atouts | **Passe** 100 % (383) | **Passe** 99 % (417) | **Passe** 99 % (121) | (peu : 6) |
| V ou 9 sec | **Passe** 100 % (124) | **Passe** 100 % (177) | **Passe** 100 % (65) | (peu : 11) |
| ni V ni 9 | **Passe** 98 % (1240) | **Passe** 98 % (1515) | **Passe** 97 % (525) | **Passe** 100 % (46) |

