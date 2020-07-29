# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name': u"OpenFire / Module Parc installé",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Parc installé : gestion des produits installés avec no de série.
""",
    'depends': [
        'product',
        'of_project_issue',
        'of_map_view',
        'of_product_brand',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/of_parc_installe_security.xml',
        'views/of_parc_installe_view.xml',
        'wizard/of_wizard_saleorder_to_parc_installe_view.xml',
    ],
    'installable': True,
}
