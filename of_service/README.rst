==========
OF Service
==========

Module de gestion des demandes d'interventions pour OpenFire.


Fonctionnalités
###############


Demandes d'intervention (`of.service.request`)
----------------------------------------------

* Les **demandes d'intervention** (DI) sont **utilisés** pour planifier des **interventions**.
    - elles sont accessibles depuis le menu **"Interventions > Interventions > Demandes d'interventions"**.

* Mise en place d'une séquence pour le nommage des demandes d'interventions sous la forme DI/XXXXXX.
    - la séquence est renseignée automatiquement lors de la validation d'une demande d'intervention.

* Mise en place de différents **champs** pour **qualifier** au mieux la demande d'intervention (**qui, quand, où, quoi**) :
    - `Type` : type de demande d'intervention (entretien, dépannage, installation, etc.);
    - `Étiquettes` : étiquettes pour qualifier l'intervention;
    - `Modèle d'intervention` : modèle d'intervention à utiliser pour le renseignement des champs;
    - `Intervenants` : intervenants qui pourront réaliser l'intervention;
    - `Client` : client concerné par la demande d'intervention;
    - `Adresse` : adresse du client concerné par la demande d'intervention;
    - `Description` : description de l'intervention;
    - `Tâches` : tâches à réaliser lors de l'intervention;
    - `Entre le JJ/MM/AAAA et le JJ/MM/AAAA` : période de réalisation de l'intervention souhaitée;
    - `Historique` : historique des interventions réalisées pour l'adresse liée à la demande d'intervention;
    - etc.

* Affichage des différents **boutons** pour passer **d'un état à l'autre** sur l'intervention.

* Mise en place d'un champ `État` pour les demandes d'intervention afin de suivre l'avancement de la demande et des interventions liées.
    - cet est calculé automatiquement en fonction des dates de début et de fin de la demande d'intervention et des dates de planification des interventions liées.
    - les valeurs possibles sont :
        - `Brouillon` : état par défaut de la demande d'intervention (en cours de saisie);
        - `Rien à planifier` : si aucune date n'a été renseignée pour la demande d'intervention;
        - `A planifier` : demande d'intervention validée avec une date de planification;
        - `Planifiée prochainement` : la date de planification est dans moins d'un mois;
        - `En retard de planification` : date de planification dépassée et aucune planification;
        - `Partiellement planifiée` : la demande d'intervention est partiellement planifiée, certaines interventions sont réalisées,
            d'autres non, et la durée restante est supérieure à 0;
        - `Entièrement planifié` : toutes les interventions sont planifiées et la durée restante est égale à 0;
        - `RDV en cours` : une intervention de la demande d'intervention est en cours de réalisation par un technicien;
        - `Terminé` : demande d'intervention entièrement planifiée et toutes les interventions sont à l'état 'Réalisé';
        - `Annulé` : la demande d'intervention est annulée.

* Mise en place d'un wizard pour créer les interventions depuis la DI

* Mise en place d'un champ `Modèle d'intervention` pour les demandes d'intervention.
    - ce champ permet de pré-remplir les champs de la demande d'intervention en fonction du modèle d'intervention sélectionné.
    - les champs pré-remplis sont :
        - la tâches;
        - le type;
        - les lignes de facturation;
        - la position fiscale.

* Mise en place d'une action pour générer un devis depuis une demande d'intervention.
    - les lignes de la DI qui ne sont pas liées à une commande ou déjà entièrement facturée sont ajoutées au devis;


Lignes de demande d'intervention (`of.service.request.line`)
------------------------------------------------------------

* Les **lignes de demande d'intervention** sont **utilisées** pour **détailler** les **demandes d'interventions**.
    - elles représentent les produits ou services à facturer pour une demande d'intervention.
    - elles sont facturables ou non (une ligne associée à une commande est non facturable)

* Les lignes de demande d'intervention portent les champs suivant :
    - `Produit` : produit ou service à facturer;
    - `Quantité` : quantité à facturer;
    - `Qté facturable` : quantité facturable de la ligne;
    - `Qté facturée` : quantité facturée de la ligne;
    - `Prix unitaire` : prix unitaire du produit ou service;
    - `TVA` : taux de TVA à appliquer;


Interventions (`calendar.event`)
--------------------------------

* Ajout d'un champ `Demande d'intervention`.
    - lors du renseignement de la demande d'intervention nous allons mettre à jours les données de l'intervention, comme :
        - la tâche;
        - l'adresse;
        - les étiquettes;
        - la commande;
        - le type;
        - ou encore les lignes ou la position fiscales dans certains cas.

* Ajout d'un type d'intervention sur les interventions ce qui permet de catégoriser les interventions et de les retrouver plus facilement.
    - certains types d'interventions sont préchargés par le module, les types sont :
        - `Entretien - Maintenance`;
        - `Installation`;
        - `Visite technique`.
    - un type d'intervention permet également de prioriser les modèles d'interventions à utiliser pour renseigner les champs de l'intervention.


Tâches (`of.planning.task`)
---------------------------

* Ajout d'un champ **"Récurrence"** sur les tâches pour planifier des tâches récurrentes qui seront utilisées pour les demandes d'interventions.

* Il est possible de prioriser l'affichage des tâches récurrentes.

* Ajout d'un smart bouton pour consulter les demandes d'interventions liées à une tâche.


Étapes (`of.service.request.stage`)
-----------------------------------

* Les **étapes** sont **utilisées** pour organiser les **demandes d'interventions** en vue Kanban.
    - elles sont accessibles depuis le menu **"Interventions > Configuration > Étapes"**.

* Les **étapes** peuvent être **limitées/autorisées** à certains **types** de demandes d'interventions.


Types (`of.service.request.type`)
---------------------------------

* Les **type** sont **utilisés** pour gérer les **interventions/demandes d'interventions/modèles d'intervention/étapes**.


Tags (`of.service.request.tag`)
-------------------------------

* Les **tags** sont **utilisés** pour catégoriser les **interventions/demandes d'interventions**.


Modèle de devis (`sale.order.template`)
---------------------------------------

* Ajout d'un champ **"Suivi des demandes d'intervention"** avec deux sélections possibles :
    - "Non";
    - "Créer une DI par bon de commande".

* Ajout d'un champ "Modèle d'intervention associé" pour sélectionner le template à utiliser pour la création de la DI.


Commandes
---------

* Ajout d'un lien vers les commandes sur les demandes d'interventions pour lier une commande à une demande d'intervention.
    - un smart boutons permet de consulter les commandes liées à une demande d'intervention.


Clients
-------

* Ajout d'un lien vers les clients sur les demandes d'interventions pour lier un client à une demande d'intervention :
    - des smart boutons permettent de consulter les DI classiques et les DI récurrentes liées à un client.


Droits utilisateurs
###################

* Ajout d'un groupe **"(OF) Interventions : Menu DI/Entretiens par défaut"**
    - ce groupe permet de faire apparaître le menu "Maintenance" en première position dans le menu principal "Interventions"
    - sans ce groupe l'ordre des menu est le suivant :
        - "Interventions"
        - "Demandes d'interventions"
        - "Maintenance"
        - etc.
    - avec ce groupe l'ordre des menu est le suivant :
        - "Maintenance"
        - "Interventions"
        - "Demandes d'interventions"
        - etc.


Reporting
#########

Ajout d'un rapport pour les demandes d'interventions.
