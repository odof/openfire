=================
OF Datastore Sale
=================

Module OpenFire / Connecteur commandes de vente


Fonctionnalités
###############


Connecteur de commandes de vente (`of.datastore.sale`)
------------------------------------------------------

* Mise en place d'un objet pour la gestion des connecteurs de commandes de vente.
    - Accessible via le menu "Paramètres > Connecteurs > Connecteurs de vente".


* Module permettant la réception automatisée des commandes de vente depuis une base OpenFire.


Marque de produit (`of.product.brand`)
--------------------------------------

* Ajout d'un champ pour savoir si la marque autorise le dropshipping.
    - Ce champ est visible si jamais le paramètre de configuration "Autoriser le dropshipping" est activé.
    - Si la case est cochée, cela mettra à jour les routes des produits liés à cette marque pour autoriser le dropshipping.


Produits
--------

* Lors du changement de marque d'un produit, les routes de ce produit sont mises à jour pour autoriser le dropshipping si la marque le permet.


Commande d'achat
----------------

* À la validation d'une commande d'achat (si il y a un connecteur pour ce fournisseur) les mouvements de stock et les BL sont liés aux éléments côtés fournisseur.


Commande de vente
-----------------

* A la fonction de confirmation de commande liée à une commande d'achat centralisée, la commande d'achat centralisée est validée automatiquement.

* Ajout d'un filtre dans la vue de recherche pour facilement trouver les commandes de vente issue d'une commande d'achat centralisée.


Paramètres de configuration
###########################

Configuration des ventes
------------------------

* Ajout d'un paramètre pour choisir l'article à utiliser pour les éléments divers du connecteur de vente.
    - Accessible via le menu Paramètres > Ventes > Facturation > **(OF) Éléments divers pour le connecteur de vente**.

Configuration des achats
------------------------

* Ajout d'un paramètre pour activer la possibilité de faire des achats en dropshipping sur les marques.
    - Accessible via le menu "Paramètres > Achats > Logistique > **(OF) Envoi direct**".
