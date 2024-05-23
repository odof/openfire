=================================
OF Company communication customer
=================================

Module de gestion des message entre base 
Module enfant (pour les bases filles) 

Information sur le module
#########################

Models
------

Ce Module apporte le model of_communication_customer_message qui hérite de of_communication_message pour crée un message sur la base enfant
Ce Module apporte le model of_communication_notification_log qui crée un log pour une notification par user


Data
-----

Ce Module apporte un CRON qui passera toute les 5 minute 

Vues
----

Ce Module apporte une vue qui hérite de la vue pour afficher tout les messages dans une liste du module parent en laissent seulement au client la possibilité de lire 
Ce Module apporte une vue qui hérite de la vue formulaire du module parent en laissent seulement au client la possibilité de lire 

Sécurité
--------

Ce module apporte une sécurité de CRUD ou tout les user on tout les droit sur le module des logs de notification
Ce module apporte une sécurité de CRUD ou tout les user excepté l'admin on le droit de seulement lire le module des messages

Static, JS / SCSS
-----------------

Ce module apporte une fonction en Java Scripte permettant de créer une notification en bannière et un pop-up(pop-up pris en compte par odoo de base)
Ce module apporte un style pour la notification bannière

Traduction
----------

Ce module apporte une traduction en français
