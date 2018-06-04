# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Rapports de vente",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': '',
    'category': 'OpenFire modules',
    "description": """
Rapports de vente OpenFire
==========================

- Ajout du champ date de pose dans les commandes
- Ajout du rapport de vente sur mesure

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_purchase",
        "of_sale",
    ],
    "category": "OpenFire",
    "data": [
        'views/of_sale_report_views.xml',
        'wizards/of_report_openflam_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
