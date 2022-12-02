# -*- coding: utf-8 -*-

{
    "name": u"OpenFire / Module de lient entre Liste de choix et kits",
    "version": "10.0.1.1.0",
    "author": "OpenFire",
    "description": u"""
Gestion des listes de choix
===========================
- Surcharge pour gérer les kits dans l'impression liste de choix
""",
    "website": "www.openfire.fr",
    "depends": [
        'of_liste_choix',
        'of_kit',
    ],
    "category": "OpenFire",
    "data": [
        'report/of_liste_choix_kit_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
