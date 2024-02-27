============
OF Equipment
============

Module de gestion des équipements pour OpenFire.


Fonctionnalités
###############

Équipements (`of.equipment`)
----------------------------

* Ajout d'un objet équipement permettant de gérer les équipements pour un client donné, sur une site donné.
    - un équipement est lié à un produit et à un partenaire;
    - il porte plusieurs informations de qualification telles que :
        - la date de vente, le N° de série, le produit, le modèle et la marque
        - le client lié, l'adresse de l'installation
        - la date d'installation, le type d'installation
        - le type de garantie, la date de fin de garantie
    - il est également possible de consulter l'historique des interventions sur un équipement.

* Mise en place de smartboutons sur l'équipement pour accéder aux ventes/factures liées.


Modèle d'intervention (`of.intervention.template`)
--------------------------------------------------

* Ajout des champs de configuration des données de l'équipement à imprimer sur les rapports/fiches d'interventions.


Client
------

* Ajout de champ de qualification (revendeur/installeur) sur un contact pour un partenaire.

* Ajout d'un smartbouton sur la fiche client pour accéder aux équipements liés.


Bon de commande
---------------

* Ajout d'un smartbouton sur la fiche de la commande pour accéder aux équipements liés.

* Mise en place d'un wizard pour la création d'un équipement depuis la commande.
    - cf. Commande > Actions > Créer un équipement.
    - le wizard reprend par défaut les informations de la commande pour la création de l'équipement :
        - produit : un produit disponible sur la commande
        - date de vente : la date de confirmation de la commande (ou la date de la commande si la commande n'est pas confirmée)
        - client : le client de la commande
        - installateur, revendeur : la fiche client de la société de la commande


Facture
-------

* Ajout d'un smartbouton sur la fiche de la facture pour accéder aux équipements liés.

* Mise en place d'un wizard pour la création d'un équipement depuis la facture.
    - cf. Facture > Actions > Créer un équipement.
    - le wizard reprend par défaut les informations de la commande pour la création de l'équipement :
        - produit : un produit disponible sur la commande
        - date de vente : la date de confirmation de la commande (ou la date de la commande si la commande n'est pas confirmée)
        - client : le client de la commande
        - installateur, revendeur : la fiche client de la société de la commande


Paramètres de configuration
###########################

Inventaire
----------

* Ajout d'un paramètre permettant de déclencher la création d'un équipement à la validation d'un BL contenant un N° de série.
    - cf. Paramètres > Inventaire > Traçabilité > **(OF) Création automatique d'équipement**.
    - Si le paramètre est activé, un équipement est créé à la confirmation du BL.


Reporting
#########

* Ajout d'un **rapport d'intervention (RI)** et d'une **fiche d'intervention (FI)** pour les interventions.
* Ajout d'options de paramétrage pour l'affichage des données sur **rapport d'intervention (RI)** et d'une **fiche d'intervention (FI)** pour les interventions.
    - il est possible de choisir les éléments suivant :
        - ÉQUIPEMENT (informations générales)
            -  N° de série
            -  Produit
            -  Modèle
            -  Marque
            -  Catégorie
            -  Date d'installation
            -  Type d'installation
            -  Conformité
            -  Installateur
            -  Note
