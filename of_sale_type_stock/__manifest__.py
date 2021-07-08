# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Types de devis - stock ventes",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    "category": "OpenFire",
    "description": u"""
Module de lien entre type de devis et stock ventes
==================================================
Type de devis
-------------
 - Ajout du type de devis dans le menu lignes de commande 

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_sale_type",
        "of_sale_stock",
        ],
    "data": [
        'views/of_sale_type_stock_views.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': True,
    }
