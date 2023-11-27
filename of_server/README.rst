=========
OF server
=========

Module OpenFire de fonctions serveur


Fonctionnalités
###############

Ce module redéfinit des fonctions de gestion des bases de données.

* Ajout de la possibilité de générer une sauvegarde (zip) d'une base avec un dossier filestore minimaliste
* Ajout de la possibilité de restaurer/dupliquer une base en nettoyant ses données sensibles

Ce module a vocation à être chargé indépendamment des bases de données.

Dans le fichier de configuration Odoo, modifier le paramètre **server_wide_modules = base,web,of_server**
