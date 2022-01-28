# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Analytique",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': '',
    "category": "OpenFire",
    "description": """
Compte Analytique OpenFire
==========================

Configuration des ventes:
-------------------------
 - Forcer l'utilisation des comptes analytiques.

Factures:
---------
 - Ajouter le compte analytique sur la facture et cacher le compte sur les lignes de factures.

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_sale",
        "analytic",
        "base",
    ],
    "data": [
        "security/of_analytique_security.xml",
        "views/of_analytique_views.xml",
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
