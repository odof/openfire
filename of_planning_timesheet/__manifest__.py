# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "OpenFire / Planning - Feuilles de temps",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    "license": '',
    "category": "OpenFire",
    "description": u"""
Module OpenFire / Planning - Feuilles de temps
==============================================
Module de gestion du temps sur les interventions
""",
    "website": "www.openfire.fr",
    "depends": [
        'of_analytique',
        'of_planning',
    ],
    "data": [
        'data/data.xml',
        "security/ir.model.access.csv",
        'views/account_views.xml',
        'views/planning_views.xml',
        'views/res_company_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

