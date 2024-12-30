==============
OF Sale Kanban
==============

Gestion des étapes Kanban pour les commandes de vente.

Fonctionnalités
################

Ventes
------

* Ajout du champ **"Nom du produit principal"** sur les commandes de vente, permettant d'afficher le nom du produit principal dans la vue Kanban.

* Modification de la vue Kanban des commandes de vente, avec un affichage conforme au modèle suivant :

    .. code-block:: text

        +-------------------------------------------------------+
        | Nom client - Montant HT de la commande                |
        +-------------------------------------------------------+
        | Numéro de la commande    | Nom du produit principal   |
        +-------------------------------------------------------+
        | Semaine de pose : YYYY - SXX                          |
        +-------------------------------------------------------+
        | Priorité | Activité | État de la commande | Vendeur   |
        +-------------------------------------------------------+


Étapes Kanban (`of.sale.order.kanban.stage`)
--------------------------------------------

* Ajout d'un **nouveau modèle** pour gérer les étapes Kanban des commandes de vente.

* Ce modèle contient les champs suivants :
    - **Séquence** : pour définir l'ordre des étapes ;
    - **Nom** : pour identifier l'étape ;

* Une étape "Nouveau" est créée par défaut lors de l'installation du module.
