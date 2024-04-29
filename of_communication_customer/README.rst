=================================
OF Company communication customer
=================================

Ce module permet de voir les messages de communication que OpenFire publie
Ce module représente la partie récepteur de message provenant d'OpenFire.

Fonctionnalités
###############

Communication (`of.communication.customer`)
-------------------------------------------

* Modification de l'objet message de communication pour la création de message à publier
    - il possède différents nouveaux champs pour la gestion du message :
        - ID du Message Source;

* Ajout d'un Cron qui récupère les message de la base d'OpenFire pour les créer dans la base Client

* Ajout d'un Hooks pour supprimer l'action de publier tout les message brouillon
