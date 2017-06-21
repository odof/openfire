# -*- encoding: utf-8 -*-

{
    'name' : "OpenFire / CRM Odoo/OpenFire",
    'version' : "9.0",
    'author' : "OpenFire",
    'website' : "http://openfire.fr",
    'category': 'Customer Relationship Management',
    'description': u""" Module OpenFire pour le CRM Odoo.
---------------------------------

Les pistes utilisent le même jeu d'étiquettes que les partenaires.
""",
    'depends' : [
        'crm',
    ],
    'data' : [
        'views/of_crm_view.xml',
    ],
    'installable': False,
}
