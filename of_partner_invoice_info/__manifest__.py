# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name': u"OpenFire / Info de facturation des clients",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Ajout d'informations liées à la facturation dans la fiche du partenaire.

- Smart-button des factures non soldées
- Smart-button des commandes à facturer
- Information d'encours maximum et de dépassement de ce montant
""",
    'depends': ['of_sale', 'of_sale_type', 'of_sale_stock'],
    'data': [
        'views/res_partner_views.xml',
        'views/of_sale_type_views.xml',
        'views/account_invoice_views.xml',
        'views/sale_order_line_views.xml',
        'wizards/of_wizard_warning.xml',
    ],
    'installable': True,
}
