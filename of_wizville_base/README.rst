======================
OF Wizville Base
======================

Module de base pour l'implémentation de l'API Wizville.

Fonctionnalités
###############

Historique Wizville (`of.wizville.history`)
-------------------------------------------

- Ajout d'un nouveau modèle pour stocker et gérer les imports/exports Wizville dans la base de données.
- Il est possible depuis cet objet de :
  - récupérer un fichier de Wizville ;
  - déposer un fichier sur le SFTP associé.

Information fournisseur produits
--------------------------------

- Ajout d'un champ "Type d'équipement" sur les informations fournisseurs.
  - Ce champ peut prendre les valeurs suivantes : Granulés, Bois, Gaz, Mixte.

Client
------

- Ajout de champs d'information Wizville sur la fiche client dans un onglet "Informations Wizville".
    - Informations disponibles :
        - Satisfaction globale ;
        - Score NPS ;
        - Date d'envoi NPS ;
        - Date de réponse NPS.

Société
-------

- Ajout d'un champ "Code Wizville" sur les sociétés.

Paramètres de configuration
############################

Wizville
--------

- Ajout d'une section "Wizville" dans la configuration des connecteurs :
  - permet de configurer les paramètres de connexion à l'API Wizville.
