# -*- coding: utf-8 -*-

{
    "name": u"OpenFire / Liste de choix",
    "version": "10.0.1.1.0",
    "author": "OpenFire",
    "description": u"""
Gestion des listes de choix
===========================
- Ajout d'un rapport devis sans prix (Liste de choix)
""",
    "website": "www.openfire.fr",
    "depends": [
        'product',
        'of_sale',
    ],
    "category": "OpenFire",
    "data": [
        'report/of_liste_choix_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
