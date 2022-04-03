# -*- coding: utf-8 -*-
{
    "name": "OpenFire / Planning - Paiements ventes",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    "license": '',
    "category": "OpenFire",
    "description": u"""
Module OpenFire / Planning - Paiements ventes
=============================================
Module intermédiaire entre le planning et les paiements ventes
""",
    "website": "www.openfire.fr",
    "depends": [
        'of_planning',
        'of_datastore_product',
    ],
    "data": [
        'reports/of_planning_fiche_intervention_templates.xml',
        'reports/of_planning_rapport_intervention_templates.xml',
        'views/of_planning_intervention_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}

