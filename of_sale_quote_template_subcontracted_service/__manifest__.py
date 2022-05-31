# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Modèle de devis avec sous-traitance",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': '',
    "category": "OpenFire",
    "description": u"""
Modèle de devis OpenFire
========================
Ce module modifie les modèles de devis OpenFire pour fonctionner avec la sous-traitance


Fonctionnalités
----------------
 - Ajout des infos de sous traitance sur les lignes de section
""",
    "website": "www.openfire.fr",
    "depends": [
        "of_sale_quote_template",
        "of_subcontracted_service",
    ],
    "data": [
        'views/of_sale_quote_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
