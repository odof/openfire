===============
OF Product Pack
===============


Module de gestion des kits de produits.

C'est un module d'extension du module `product_pack` afin de modifier quelques comportements de ce dernier pour satisfaire nos besoins.


Fonctionnalités
###############


Produits
--------

* Modification du champ **"Type de kit"** afin de le rendre **obligatoire** et de mettre une valeur par **défaut (non détaillé)**.

* Suppression de l'option "détaillé" du champ "Prix des composants du kit".

* Modification de la fonction `_is_pack_to_be_handled` pour que l'option **"non détaillé"** permette de choisir une **option de prix de kit**.
    - dans le module **OCA** `product_pack`, l'option "non détaillé" **ne permet pas** de choisir une option de prix de kit.

* Renommage des choix "Ignoré" en "Fixé" et "Totalisé dans l'article principal" en "Calculé".

* Suppression de la condition d'affichage entre "Type d'affichage du kit" et "Prix des composants du kit".
