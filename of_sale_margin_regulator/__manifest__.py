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
        'of_sale_stock',
    ],
    'data': [
        'reports/of_sale_margin_regulator_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}