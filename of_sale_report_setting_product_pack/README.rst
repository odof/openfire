=======================
OF Sale Report Settings
=======================


Module de lien entre la gestion des kits de produits dans les ventes et les paramètres de rapport de vente.


Fonctionnalités
###############


Ventes
------

* Ajout d'un champ `Impression des kits` dans le formulaire de la commande de vente.
    - Cela permet de choisir le type d'impression du kits sur le rapport de vente.
    - Les valeurs possibles sont:
        - `Kit uniquement`: Seulement les kits sont présents sur le rapport (sans les composants).
        - `Kit et composants`: Les kits et les composants sont présents sur le rapport mais sans détails des prix pour les composants.
        - `Kit et composants avec détails des prix`: Les kits et les composants sont présents sur le rapport avec les détails des prix pour les composants (les prix du kit ne sont plus affichés).


Reporting
#########

* Modification du rapport de vente pour prendre en compte le champ `Impression des kits` de la commande de vente.
    - Si le champ `Impression des kits` est à `Kit uniquement`, le rapport affiche seulement les kits.
    - Si le champ `Impression des kits` est à `Kit et composants`, le rapport affiche les kits et les composants sans détails des prix pour les composants.
    - Si le champ `Impression des kits` est à `Kit et composants avec détails des prix`, le rapport affiche les kits et les composants avec les détails des prix pour les composants.
