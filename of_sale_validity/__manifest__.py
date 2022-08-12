# -*- coding: utf-8 -*-
{
    'name': "Openfire / OF Sale validity",
    'summary': "Module de liaison entre 'OF Sale' et 'Sales validity'",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'description': u"""
Permet la laisaison des deux modules pour une modification de vue.
""",
    'depends': [
        'base',
        'sale_validity',
        'of_sale'
    ],
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': 'Sale',
    'data': [
        'views/sale_order_view.xml',
    ],
    'auto_install': True,
    'installable': True,
 }
