==========
OF product
==========

Module de gestion des produits pour OpenFire.


Fonctionnalités
################

Produits
---------

* Mettre par défaut la référence produit (default_code) de l'article de base lors de la création d'une variante

* Ajout d'une partie "Structure de prix" sur la fiche produir avec les couts de transports/ventes, les taxes et frais divers, etc.

* Ajout de champs sur la liste des fournisseurs : Remise, Catégorie fournisseur, prix publique hors taxes, etc.


Étiquettes de produits
----------------------

* Ajout d'une description sur les étiquettes de produits

* Ajout de la possibilité d'archiver les étiquettes de produits


Paramètres de configuration
###########################

* Ajout d'un paramètre de configuration pour permettre de gérer le prix d'un produit par ses variantes :
    - "Par attribut" : Le prix de vente est géré par le modèle de produit et vous pouvez ajouter un prix supplémentaire à la variante (comportement standard);
    - "Par variante" : Le prix de vente est spécifié/forcé par variante. Il n'y a plus de prix supplémentaire.
