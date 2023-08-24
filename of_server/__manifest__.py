# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Serveur",
    'version': "10.0.1.1.0",
    'author': "OpenFire",
    'license': 'AGPL-3',
    'category': "OpenFire",
    'description': u"""
Module OpenFire de fonctions serveur
====================================

Ce module redéfinit des fonctions de gestion des bases de données.

- Ajout de la possibilité de générer une sauvegarde (zip) d'une base avec un dossier filestore minimaliste
- Ajout de la possibilité de restaurer/dupliquer une base en nettoyant ses données sensibles

Ce module a vocation à être chargé indépendamment des bases de données.

Dans le fichier de configuration Odoo, modifier le paramètre : server_wide_modules = web,web_kanban,of_server
""",
    'website': "www.openfire.fr",
    'depends': [
        'web',
    ],
    'data': [],
    # Il n'y a pas de raison d'installer ce module, il doit être chargé avec le serveur et c'est suffisant
    'installable': False,
}
