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
    'name': u"OpenFire / Commissions",
    'version': "10.0.1.1.0",
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'summary': u"Personnalisation des ventes OpenFire",
    'description': u"""
Module OpenFire / Commissions
=============================

""",
    'depends': [
        'of_account',
        'of_sale',
        'of_sale_payment',
    ],
    'data': [
        'security/of_sale_commi_security.xml',
        'security/ir.model.access.csv',
        'views/of_sale_commi_views.xml',
        'wizards/of_sale_commi_pay_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
