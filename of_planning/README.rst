===========
OF Planning
===========

Module de gestion des interventions et des plannings des techniciens pour OpenFire.


Fonctionnalités
###############

Événements (`calendar.event`)
-----------------------------

* Les **événements** Odoo sont **utilisés** pour gérer les **interventions**.

* Un **type d'événement** `Intervention` est ajouté afin de pouvoir les** différencier des autres événements Odoo**.
    - les valeurs possibles pour le champ `Type` sont : `Intervention`, `Événement`.

* Mise en place de différents **champs** pour les événements afin de **qualifier** l'intervention (**qui, quand, où, quoi**) :
    - `Technicien` : technicien en charge de l'intervention;
    - `Équipe`: équipe en charge de l'intervention;
    - `Client` : client concerné par l'intervention;
    - `Adresse` : adresse du client concerné par l'intervention;
    - `Description` : description de l'intervention;
    - `Étiquettes` : étiquettes pour qualifier l'intervention;
    - `Tâches` : tâches à réaliser lors de l'intervention;
    - etc.

* Affichage des différents **boutons** pour passer **d'un état à l'autre** sur l'intervention.

* Mise en place d'un champ `Statut` pour les intervention afin de suivre l'avancement de l'intervention :
    - `Brouillon` : l'intervention est en cours de création;
    - `Confirmé` : l'intervention est confirmée, elle peut être planifiée ou en cours;
    - `Terminée` : l'intervention est terminée;
    - `Annulée` : l'intervention est annulée;
    - `Reportée` : l'intervention est reportée.

* Ajout d'un modèle `of.planning.intervention.template` pour les interventions.
    - ce champ permet de pré-remplir les champs de l'intervention en fonction du modèle d'intervention sélectionné.
    - les champs pré-remplis sont :
        - la tâches;
        - le type;
        - les lignes de facturation;
        - la position fiscale.

* Mise en place de Smart bouton dans les interventions afin de pouvoir accéder aux ressources liées :
    - commandes
    - factures;
    - bons de livraison.

* Affichage des montants de la commande à l'origine de l'intervention :
    - `Montant HT` : montant HT de la commande;
    - `Montant Taxes` : montant des taxes de la commande;
    - `Montant TTC` : montant TTC de la commande.
    - `Montant Restant dû` : montant restant à payer sur la commande.

* Mise en place d'une liste de ligne d'intervention (`of.planning.intervention.line`) afin de pouvoir détailler les produits ou services à facturer lors de l'intervention.

* Ajout d'un onglet `Compte rendu` pour les interventions afin de pouvoir des informations sur le déroulé de l'intervention :
    - **un champ texte** permet de saisir un **compte rendu** de l'intervention;
    - deux **champs images** permettent de joindre les **signatures du client et du technicien** au compte rendu;
    - **différents champs horaires** permettent de saisir les heures de début et de fin de l'intervention ainsi que les **durées de trajet/pause**.

* Ajout d'un onglet `Photos` pour les interventions afin de pouvoir ajouter des photos à l'intervention.

* Mise en place d'une action pour pour créer des factures depuis la demande d'intervention.
    - les lignes de la DI qui ne sont pas liées à une commande ou déjà entièrement facturée sont ajoutées à la facture;

* Mise en place d'une action pour pour créer des bons de livraisons depuis la demande d'intervention.
    - les lignes de la DI qui ne sont pas liées à une commande sont ajoutées au bon de livraison;

* Mise en place de différents Smartbouton indiquant le nombre d'éléments liés à une DI et qui permet de les consulter :
    - Commandes;
    - Factures;
    - Bons de livraisons;


Ligne d'intervention (`of.planning.intervention.line`)
------------------------------------------------------

* Les **lignes d'intervention** sont **utilisées** pour **détailler** les **interventions**.
    - elles représentent les produits ou services à facturer pour une intervention.
    - elles sont facturables ou non (une ligne associée à une commande est non facturable)

* Les lignes d'intervention portent les champs suivants :
    - `Produit` : produit à utiliser lors de l'intervention;
    - `Quantité` : quantité du produit à utiliser lors de l'intervention;
    - `Prix unitaire` : prix unitaire du produit;
    - `Remise` : remise sur le produit;
    - `Taxes` : taxes sur le produit;
    - `Prix total` : prix total de la ligne d'intervention.
    - `Qté livré` : quantité livrée du produit;
    - `Qté facturé` : quantité facturée du produit;
    - `Qté facturable` : quantité facturable du produit.

* Mise en place d'un champ `Statut de facturation` pour les lignes d'intervention afin de suivre l'avancement de la facturation de la ligne d'intervention :
    - `Rien à facturer` : la ligne d'intervention n'est pas facturée;
    - `En attente de facturation` : la ligne d'intervention est à facturer;
    - `Totalement facturé` : la ligne d'intervention est entièrement facturée.


Modèle d'intervention (`of.planning.intervention.template`)
-----------------------------------------------------------

* Les **modèles d'intervention** sont **utilisés** pour **pré-remplir** les **interventions**.
    - ils permettent de pré-remplir les champs des interventions en fonction du modèle choisi.

* Les **modèles d'intervention** permettent de choisir les **informations** qu'on souhaite voir **apparaître** sur les rapport d'intervention (**RI**) et les fiches d'intervention (**FI**).
    - si aucun modèle n'est choisi, les informations de modèle d'intervention par défaut seront utilisées.
        - un modèle d'intervention par défaut est créé à l'installation du module et il ne peut pas être supprimé.

Etiquettes d'intervention (`of.planning.tag`)
---------------------------------------------

* Les étiquettes d'intervention  sont utilisées pour qualifier les interventions.


Équipes (`of.planning.team`)
----------------------------

* Les équipes sont utilisées pour gérer les équipes de techniciens.


Employés
--------

* Ajout de champs pour catégoriser l'employé en tant que technicien ou commercial.

* Ajout d'un champ `Équipe` pour les employés afin de pouvoir les rattacher à une équipe.

* Ajout d'un champ `Tâches` pour les employés afin de pouvoir les rattacher à des tâches auxquelles ils sont habilités.
    - Les tâches non présentes dans la liste l'empêcheront de réaliser des interventions liées à ces tâches.

* Ajout d'un champ `Apte à toutes les tâches` pour les employés afin de pouvoir les rendre apte à toutes les tâches.
    - ce champ est coché par défaut pour tous les employés.

* Ajout d'un champ `Envoyer un email la veille du rendez-vous` pour permettre d'envoyer un mail le soir au technicien pour lui rappeler ses rendez-vous du lendemain.
    - c'est une action planifiée qui enverra le planning du lendemain par email à tous les techniciens de toutes les sociétés qui ont ce champ coché.


Photos (`of.planning.image`)
----------------------------

* Les photos sont utilisées pour ajouter des photos aux interventions.
    - elles sont stockées dans le modèle `of.planning.image`.
    - elles sont liées à une intervention.
    - elles sont basées sur le modèle `Image` standard d'Odoo.


Clients
-------

* Mise en place de smart button dans les clients afin de pouvoir accéder aux interventions liées.

* Le champ "Secteur technique" est renseigné automatiquement en fonction du code postale si le paramètre de configuration "Secteur technique automatique" est activé.


Lignes de commande
------------------

* Mise en place d'une liaison entre les lignes de commande et les lignes d'intervention afin de pouvoir suivre l'avancement de la facturation des lignes d'intervention.

* Mise en place d'un champ "Qté réalisé" qui permet de suivre la quantité réalisée sur la ligne d'intervention.

* Mise en place d'un champ "Statut planning" qui permet de suivre l'avancement de la ligne d'intervention :
    - `À planifier` : la ligne d'intervention n'est pas planifiée;
    - `Planifié` : la ligne d'intervention est planifiée ou en cours de réalisation;
    - `Terminé` : la ligne d'intervention est terminée.


Droits utilisateurs
###################


* Ajout d'un groupe **"Accéder à mes interventions"**
    - les utilisateurs de ce groupe ne pourront accéder qu'à leurs interventions et ne modifier que leurs interventions.

* Ajout d'un groupe **"Gérer mes interventions"** qui hérite des accès du groupe **"Accéder à mes interventions"**
    - les utilisateurs de ce groupe pourront accéder à toutes les interventions mais ne pourront modifier que leurs interventions.

* Ajout d'un groupe **"Responsable"** qui hérite des accès du groupe **"Gérer mes interventions"**
    - les utilisateurs de ce groupe pourront accéder à toutes les interventions et pourront modifier toutes les interventions.
    - ils pourront également avoir accès à la configuration des interventions, mais ne pourront pas supprimer les ressources.

* Ajout d'un groupe **"Manager"** qui hérite des accès du groupe **"Responsable"**
    - les utilisateurs de ce groupe pourront accéder à toutes les interventions et pourront modifier toutes les interventions.
    - ils pourront également avoir accès à la configuration des interventions, et pourront supprimer les ressources.

* Ajout d'un groupe **"Bloquer l'accès à la configuration des interventions"**
    - les utilisateurs de ce groupe ne pourront pas accéder à la configuration des interventions.
    - c'est un groupe en plus pour bloquer unitairement l'accès à la configuration des interventions.

* La hiérarchie des groupes est donc la suivante, du plus permissif au moins permissif:
    - *Manager > Responsable > Gérer mes interventions > Accéder à mes interventions*.


Paramètres de configuration
###########################

Intervention
------------

* Ajout d'un paramètre pour choisir d'afficher ou non le montant restant dû sur les fiches d'interventions.
    - cf. Paramètres > Planning > Rapport d'intervention > **(OF) Masquer le montant restant**.

* Ajout d'un paramètre permettant de choisir la société par défaut pour les interventions lors de leur création.
    - cf. Paramètres > Planning > Interventions > **(OF) Choix de la société pour les interventions**.
    - Il est possible de choisir entre la société de l'utilisateur connecté ou la société du contact du client de l'intervention.

* Ajout d'un paramètre permettant d'activer ou non l'affectation automatique des secteurs techniques sur la fiche client.
    - cf. Paramètres > Planning > Interventions > **(OF) Affectation auto. des secteurs**.
    - Si le paramètre est activé, le secteur technique du client sera automatiquement renseigné en fonction du code postal du client.

* Ajout d'un paramètre permettant de gérer les BL sur les interventions.
    - cf. Paramètres > Planning > Interventions > **(OF) BL des interventions**.
    - Si le paramètre est activé, les lignes d'intervention provoqueront la création d'un BL lors de la validation d'intervention.


Reporting
#########

* Ajout d'un **rapport d'intervention (RI)** et d'une **fiche d'intervention (FI)** pour les interventions.
    - les **données affichées** sur les rapports sont **configurables** à travers les **modèles d'intervention**.
    - il est possible de choisir les éléments suivant :
        - INTERVENTION (informations générales)
            -  Client
            -  Code client
            -  Description de la tâche
            -  Date de début
            -  Durée
            -  Techniciens
            -  Société
            -  Titre
            -  Adresse
            -  Contact
            -  Type d'intervention
            -  Description interne/externe
        - HISTORIQUE (historique des interventions liées à l'intervention courante)
        - COMMANDE (commande liée à l'intervention)
            - Nom
            - Date de confirmation
            - Vendeur
            - Date VT
            - Totaux
            - Notes d'intervention
        - PRODUITS ET TRAVAUX (lignes de commande liées à l'intervention)
        - LIVRAISON (lignes de livraison liées à l'intervention)
        - FACTURATION (lignes de l'intervention)
        - QUESTIONNAIRE (questionnaire lié à l'intervention)
        - COMPTE RENDU
            - Dates réelles
            - Durée réelle
            - Compte rendu
        - PHOTOS
        - SIGNATURES
            - Date de signature

* Ajout de rapports pour afficher le planning des interventions :
    - planning journée/semaine/général semaine;
    - ces rapports sont utilisés à partir d'un wizard accessible depuis le menu "Interventions > Interventions > Impressions".
        - il sera demandé de choisir une date de début pour l'impression des interventions, les employés et le type de planning à imprimer.
