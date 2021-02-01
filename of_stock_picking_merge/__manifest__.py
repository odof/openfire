# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Fusion des opérations de stock",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'license': '',
    'summary': u"Openfire Fusion des opérations de stock",
    'description': u"""
Module OpenFire / Fusion des opérations de stock
================================================

Fonctionnalités
---------------
- Ajout de la possibilité de fusionner des opération de stock de même type
""",
    'depends': [
        'stock',
        'of_purchase_fusion',
    ],
    'data': [
        'wizards/of_stock_picking_merge_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
