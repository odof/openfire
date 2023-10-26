======
OF crm
======

Module de gestion de la CRM pour OpenFire


Fonctionnalités
###############


Leads et opportunités
---------------------

* Les **étiquettes des partenaires** sont utilisées pour les pistes et les opportunités

* Ajout d'une **liste d'actions (activités)** dans les pistes et les opportunités

* Ajout d'un **bouton** pour créer une **nouvelle activté** dans les pistes et les opportunités

* Ajout des quelques champs de qualication dans les pistes et les opportunités :
    - Référence;
    - Prospecteur;
    - Date de clôture;
    - Référé par;
    - Information complémentaire.

* Ajout d'un **champ de complétion pour la ville** et le code postal dans les pistes et les opportunités

* Ajout de la possibilité de voir la prochaine activité depuis la vue Kanban

* Déplacement de quelques champs standard dans la partie **"Qualification et suivi"**

* Ajout d'une **coloration rouge** sur la **liste** des pistes et des opportunités si la **"Date de prochaine action" est dépassée**


Étape CRM
---------

* Ajout d'une automatisation des étapes de la CRM
    - il est possible de définir une régle pour passer dans une étape en fonction des données;
    - il faut hériter d'un modèle spécifique pour permettre l'automatisation des étapes;



Clients
-------

* Ajout d'un **onglet "Marketing"** sur la fiche formulaire des partenaires

* Ajout de **champs de qualification** dans l'onglet **"Marketing"** des partenaires
    - ces champs récupèrent les informations suivantes des opportunités liées au client :
        - Campagne;
        - Canal;
        - Source.

* Le champ vendeur est renseigné par défaut avec l'utilisateur connecté lors de la création d'un nouveau client


Activités CRM
-------------

* Ajout des **activités CRM** dans le **menu "Activités"**
    - cet objet permet d'**apporter** une **liste de tâches à réaliser** pour un objet (par exemple les opportunités);
    - il est possible de **re-calculer la date d'échéance** de cette activité de manière **automatique** en fonction d'un **champ de l'objet**;
    - les activités terminées ne sont pas supprimées, elles sont archivées.

* Cet objet **ne remplace par les activités** standard d'Odoo, il permet de **les compléter**
    - lorsqu'une activité standard est terminée elle est supprimée;
    - lorsqu'une activité CRM est terminée elle est archivée et on garde une trace des tâches.



Type d'activités
----------------

* Customization des types d'activités standard qui sont également utilisés pour nos activités CRM
    - Ajout de différents champs :
        - Délais;
        - Équipe CRM;
        - Assigné à;
        - Modèle autorisé pour ce type d'activité;
        - Date de l'objet sur laquelle se baser;
        - Recalcul automatique de la date d'échéance;
        - Ajout d'une pièce point autorisée.
