# -*- encoding: utf-8 -*-

{
    "name" : "OpenFire / CRM Odoo",
    "version" : "1.0",
    "author" : "OpenFire",
    "website" : "http://www.openfire.fr",
    'category': 'Customer Relationship Management',
    "description": u""" Module OpenFire pour le CRM Odoo.
---------------------------------

Les pistes utilisent le même jeu d'étiquettes que les partenaires.
""",
    "depends" : [
        'crm',
    ],
    "init_xml" : [ ],
    "demo_xml" : [ ],
    'css' : [ ],
    "data" : [
        'views/of_crm_odoo_view.xml',
    ],
    "installable": True,
    'active': False,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
