# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Prévision de Vente",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Prévision de Vente OpenFire
==================================

Ce module permet d'anticiper les approvisionnements en tenant compte des ventes passées, et des ventes prévues sur la période.
------------------------------------------------------------------------------------------------------------------------------

""",
    'depends': [
        'of_sale',
        'of_stock',
        'of_gesdoc',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/of_sale_forecast_templates.xml',
        'views/of_sale_forecast_views.xml',
        'reports/of_sale_forecast_report_views.xml',
        'wizards/of_sale_forecast_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
