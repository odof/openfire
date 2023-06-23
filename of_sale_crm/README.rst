===========
OF Sale crm
===========

Module de lien entre la gestion des ventes et la CRM pour OpenFire.


Fonctionnalités
################

Clients
-------

* Ajout du champ **"État"** sur le formulaire client qui comporte plusieurs valeurs :
    - **"Prospects"** : un client qui n'a **pas de commande ou de facture validée**
    - **"Client signé"** : un client qui a **au moins une commande validée**
    - **"Autre"** : catégorisation de client ne correspondant pas aux deux autres états.

* Ajout de l'option d'avertissement "Opportunité"


CRM
---

* Ajout d'un **label informatif** sur l'étiquette de l'opportunité pour indiquer si c'est un **prospect** ou un **client signé**.


Ventes
------

* Modifications des états de la commande pour **ajouter une étape de départ "Estimation"**
    - cet état est managé par les groupes spéciaux ajoutés **"Commandes créés à l'étape Estimation"** et **"Commandes créés à l'étape Devis"**.

* Ajout d'un **nouveau champ** pour flaguer les **commandes envoyées** par la fenêtre d'envoie **d'email**

* Modification des filtres de la liste des commandes :
    - pour prendre en compte l'état "Estimation";
    - pour ajouter un filtre sur les commandes envoyées par email.


Facturation
-----------

* Ajout du champ "Prospecteur" sur les factures




Droits utilisateurs
###################

* Ajout de groupes "Commandes créés à l'étape Estimation" et "Commandes créés à l'étape Devis"


Paramètres de configuration
###########################

Ventes
------

* Ajout d'option pour activer ou non les étapes de départ "Estimation" et "Devis" sur les commandes



Reporting
#########

* Modification du rapport d'analyse de ventes pour pourvoir chercher par "Prospecteur"

* Modification du rapport d'analyse de facturation pour :
    - rechercher par "Prospecteur"
    - rechercher par "Étiquette du client".
