======
OF crm
======

Module de gestion de la CRM pour OpenFire


Fonctionnalités
###############


Leads et opportunités
---------------------

* Les **étiquettes des partenaires** sont utilisées pour les pistes et les opportunités

* Ajout des quelques champs de qualication dans les pistes et les opportunités :
    - Référence;
    - Prospecteur;
    - Date de clôture;
    - Référé par;
    - Information complémentaire.

* Ajout d'un **champ de complétion pour la ville** et le code postal dans les pistes et les opportunités

* Déplacement de quelques champs standard dans la partie **"Qualification et suivi"**


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
