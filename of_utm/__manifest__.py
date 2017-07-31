# -*- coding: utf-8 -*-

{
    'name' : "OpenFire UTM",
    'version' : "10.0",
    'author' : "OpenFire",
    'website' : "http://openfire.fr",
    'category': 'OpenFire modules',
    'description': u"""
Module OpenFire extension de UTM Odoo
=====================================

 - Ajout du champ source_ids dans utm.medium
 - Ajout du champ medium_id et sequence dans utm.source
""",
    'depends' : [
        'utm',
    ],
    'data' : [
        'views/of_utm_views.xml',
    ],
    'installable': True,
}
