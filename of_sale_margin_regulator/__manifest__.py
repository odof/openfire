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
        'of_followup',
        'of_access_control',
        'of_external',
        'sale',
    ],
    'data': [
        'reports/of_sale_margin_regulator_views.xml',
        'reports/of_external_report_templates.xml',
        'security/ir.model.access.csv',
        'wizards/of_sale_order_closure_wizard_views.xml',
        'wizards/of_sale_order_confirmation_views.xml',
        'views/sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
