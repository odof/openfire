# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'website': u"www.openfire.fr",
    'category': u"OpenFire",
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
        'wizards/of_sale_order_gestion_prix_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
