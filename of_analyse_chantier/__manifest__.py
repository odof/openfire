# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Analyse de chantier",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': '',
    "category": "OpenFire",
    "description": """
Analyse de chantier OpenFire
==========================


""",
    "website": "www.openfire.fr",
    "depends": [
        "of_purchase",
        "of_sale",
        "of_account",
        "of_kit",
        "of_planning",
        "analytic"
    ],
    "data": [
        "views/of_analyse_chantier_views.xml",
        "wizards/of_analyse_chantier_wizard_views.xml",
        "security/of_analyse_chantier_security.xml",
        "security/ir.model.access.csv",
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
