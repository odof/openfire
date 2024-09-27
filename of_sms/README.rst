======
OF SMS
======


Fonctionnalités
###############


Expéditeur (`of.sms.sender`)
----------------------------

*  Ajout d'un modèle pour les expéditeurs de SMS avec les champs suivants :
    - Nom;
    - Nom de l'expéditeur;
    - Modèle;

* Cela permet de définir des expéditeurs de SMS en fonction du modèle Odoo (partenaire, intervention, etc.).

* Ajout d'un expéditeur "Sans nom" qui permet d'envoyer des SMS sans avoir à configurer de noms d'expéditeurs chez OVH.


SMS (`sms.sms`)
---------------

* Ajout de champs pour les SMS :
  - Expéditeur;
  - Est commercial;
  - Date d'envoi;

* Ajout d'un état "À envoyer" pour les SMS qui n'ont pas encore été envoyés.

* Ajout d'une action planifiée pour l'envoi des SMS différés
  - Les SMS sont changés de statut de "À envoyer" à "Dans la file d'attente" et seront envoyés à la prochaine exécution de l'action planifiée qui envoie les SMS.
