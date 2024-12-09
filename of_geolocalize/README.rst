==============
OF Geolocalize
==============

Module d'extension du module de géolocalisation de Odoo (base_geolocalize)


Fonctionnalités
###############


Contact
-------

* Lors de la **création ou de la mise à jour** d'un contact les **informations de geocaodage** seront **mises à jour** en fonction des paramètres de configuration choisis.
* Ajout d'un menu dans l'application "Contact" pour ouvrir les configuration de géocodage : **"Contacts > Configuration > Paramètres de géolocalisation > Géolocalisation"**
* Ajout et affichage de champs d'état de géocodage et la réponse json de openstreetmap dans la vue formulaire des contacts.
* Affichage de la carte dans la vue formulaire des contacts.

Paramètres de configuration
###########################

* Ajout d'un **paramètre** de configuration pour le géocodage à la **modification de l'adresse**
    - les choix possibles sont :
        - Ne pas recalculer automatiquement les valeurs de géolocalisation (les coordonnées GPS sont remises à zéro);
        - Recalculer automatiquement les valeurs de géolocalisation.

* Ajout d'un **paramètre** de configuration pour le géocodage à la **création d'une adresse**
    - les choix possibles sont :
        - Ne pas calculer automatiquement les valeurs de géolocalisation (option recommandée avant de lancer l'import d'un grand nombre de contacts);
        - Calculer automatiquement les valeurs de géolocalisation.
