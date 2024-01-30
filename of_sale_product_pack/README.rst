====================
OF Sale Product Pack
====================

Module de gestion des kits de produits dans les ventes.

C'est un module de lien et d'extension du module `sale_product_pack` afin de modifier quelques comportements de ce dernier pour satisfaire nos besoins.


Ligne de commande
-----------------

* Ajout du champs **"Affichage du kit"** sur la ligne de commande pour rende configurable l'affichage du kit sur la ligne de commande.
    - Cela permet de changer l'affichage du kit sur la ligne de commande et de ne pas modifier le comportement global du kit.
    - Les valeurs possibles sont :
        - "Détaillé" : Cela provoquera la création des lignes pour chaque composant du kit;
        - "Non détaillé" : Cela provoquera la création d'une seule ligne pour le kit.

* Ajout d'un champ **"Kit de produits"** sur la ligne de commande pour afficher les composants du kit à la ligne de commande.
    - cela permet :
        - de visualiser les composants du kit directement sur la ligne de commande;
        - ajouter/retirer éventuellement des composants au kit sans pour autant modifier le kit lui-même.
