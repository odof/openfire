============
OF Equipment
============

Module de gestion des équipements pour OpenFire.

Fonctionnalités
###############

Équipements (`of.equipment`)
----------------------------

- Ajout d'un objet équipement permettant de gérer les équipements pour un client donné, sur un site donné.
    - Un équipement est lié à un produit et à un partenaire.
    - Il contient plusieurs informations de qualification telles que :
        - la date de vente, le N° de série, le produit, le modèle et la marque ;
        - le client lié et l'adresse de l'installation ;
        - la date et le type d'installation ;
        - le type de garantie et la date de fin de garantie.
    - Il est également possible de consulter l'historique des interventions sur un équipement.

- Mise en place de smartboutons sur l'équipement pour accéder aux ventes et factures liées.

Modèle d'intervention (`of.intervention.template`)
--------------------------------------------------

- Ajout de champs de configuration des données de l'équipement à imprimer sur les rapports et fiches d'interventions.

Rapport d'équipement (`of.equipment.intervention.report.template`)
------------------------------------------------------------------

- Un **rapport d'équipement** est similaire au modèle d'intervention et **permet de préconfigurer** les données pour un équipement lié à une intervention afin de préciser son déroulé.

- Il est possible de spécifier sur le modèle de rapport :
    - une tâche par défaut pour l'équipement ;
    - un mode d'envoi pour le rapport d'équipement (fusionné ou séparé) :
        - En mode **fusionné**, les équipements sont **regroupés dans le rapport d'intervention**.
        - En mode **séparé**, chaque équipement a son propre rapport d'intervention **attaché à l'email de l'intervention**.
    - des lignes de facturation par défaut pour l'équipement ;
    - un questionnaire par défaut pour l'équipement.

- Les rapports d'équipement sont accessibles depuis le menu : **`Interventions > Configuration > Rapport d'équipement`**.

Intervention (`calendar.event`)
-------------------------------

- Ajout d'une **liste d'équipements** liés à une intervention.
    - Cette liste est visible dans la partie **"Quoi"** de l'intervention, **si la case "Équipements" est cochée**.
    - Il est possible d'ajouter un équipement individuellement depuis la liste ou en masse depuis le smartbouton `Ajouter des équipements`.
    - Il est possible d'ajouter plusieurs fois le même équipement sur une intervention.
    - Lors de l'ajout, on précise le rapport d'équipement à utiliser pour l'équipement.

- Le **calcul de la durée** de l'intervention **prend en compte les équipements liés** :
    - Durée de l'intervention = ([Durée de la tâche de l'intervention] × [Nombre de liens d'équipements sans tâche]) + [Somme des durées des tâches des liens d'équipement].

- Lors de **l'envoi de l'intervention par email**, les rapports d'équipement **en mode "attaché" sont ajoutés** au composer de l'email avec le rapport d'intervention.

Lien d'équipement d'intervention (`of.calendar.event.equipment.link`)
---------------------------------------------------------------------

- Ajout d'un objet de **lien entre une intervention et un équipement**.

- Il permet de **lier un équipement à une intervention** et de spécifier son déroulé :
    - Un bouton "Compte rendu" sur le lien d'équipement permet d'accéder au déroulé.
    - Dans ce compte rendu, il est possible de saisir :
        - un compte rendu texte ;
        - des photos ;
        - un questionnaire ;
        - des lignes de facturation.

- Lors de l'ajout d'une ligne de facturation à un lien d'équipement :
    - La ligne est automatiquement liée à l'intervention.
    - Les modifications effectuées depuis le lien d'équipement sont répercutées sur l'intervention et inversement.
    - Un message est posté dans le flux pour prévenir l'utilisateur.

Client
------

- Ajout de champs de qualification (revendeur/installeur) sur un contact pour un partenaire.

- Ajout d'un smartbouton sur la fiche client pour accéder aux équipements liés.

Bon de commande
---------------

- Ajout d'un smartbouton sur la fiche de la commande pour accéder aux équipements liés.

- Mise en place d'un assistant pour la création d'un équipement depuis la commande :
    - Chemin : **`Commande > Actions > Créer un équipement`**.
    - Le wizard reprend par défaut les informations de la commande :
        - Produit : un produit disponible sur la commande ;
        - Date de vente : la date de confirmation de la commande (ou la date de la commande si non confirmée) ;
        - Client : le client de la commande ;
        - Installateur, revendeur : la fiche client de la société de la commande.

Facture
-------

- Ajout d'un smartbouton sur la fiche de la facture pour accéder aux équipements liés.

- Mise en place d'un wizard pour la création d'un équipement depuis la facture :
    - Chemin : **`Facture > Actions > Créer un équipement`**.
    - Le wizard reprend par défaut les informations de la commande pour la création de l'équipement :
        - Produit : un produit disponible sur la commande ;
        - Date de vente : la date de confirmation de la commande (ou la date de la commande si non confirmée) ;
        - Client : le client de la commande ;
        - Installateur, revendeur : la fiche client de la société de la commande.

Paramètres de configuration
###########################

Inventaire
----------

- Ajout d'un paramètre permettant de déclencher la création d'un équipement à la validation d'un bon de livraison contenant un N° de série :
    - Chemin : **`Paramètres > Inventaire > Traçabilité > (OF) Création automatique d'équipement`**.
    - Si le paramètre est activé, un équipement est créé à la confirmation du BL.

Reporting
#########

- Ajout d'un **rapport d'intervention (RI)** et d'une **fiche d'intervention (FI)** pour les interventions :
    - Le rapport d'intervention reprend les informations de l'intervention et des équipements liés en mode fusionné.

- Ajout d'options de paramétrage pour l'affichage des données sur les rapports d'intervention :
    - ÉQUIPEMENT (informations générales) :
        - N° de série ;
        - Produit ;
        - Modèle ;
        - Marque ;
        - Catégorie ;
        - Date d'installation ;
        - Type d'installation ;
        - Conformité ;
        - Installateur ;
        - Note.

- Ajout d'un **rapport d'équipement (RE)** pour les équipements :
    - Imprimable pour un équipement donné depuis la liste des liens d'équipements de l'intervention.
    - Le rapport d'équipement reprend les informations de l'équipement et de l'intervention liée.
    - Configuration des données à afficher, comme pour le modèle d'intervention.
