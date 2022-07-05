# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#
##############################################################################

{
    'name': u"OpenFire / Ventes / Budget",
    'version': "10.0.1.0.0",
    'license': '',
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'summary': u"Gestion du budget OpenFire",
    'description': u"""
Module OpenFire / Ventes / Budget
=================================

""",
    'depends': [
        'of_sale_quote_template_subcontracted_service',
        'of_sale_planning',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/of_sale_budget_data.xml',
        'views/of_sale_budget_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
