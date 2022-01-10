# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Régule de marge",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Régule de marge OpenFire
======================================

Ce module ajoute le rapport Régule de marge pour les ventes
""",
    'depends': [
        'of_account_margin',
        'of_external',
        'of_sale_custom_workflow',
    ],
    'data': [
        'reports/of_sale_margin_regulator_views.xml',
        'reports/of_price_variation_analysis_views.xml',
        'security/ir.model.access.csv',
        'security/of_sale_margin_regulator_security.xml',
        'views/sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
