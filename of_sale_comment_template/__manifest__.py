# -*- coding: utf-8 -*-
{
    'name': "Openfire / OF Sale Comments template",
    'summary': "Module de liaison entre 'OF Sale' et 'Sales Comments'",
    'version': '10.0.1.0.0',
    'description': u"""
Permet la laisaison des deux modules.
""",
    'depends': [
        'base',
        'sale_comment_template',
        'of_sale'
    ],
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': 'Sale',
    'license': 'AGPL-3',
    'data': [
        'views/sale_order_view.xml',
    ],
    'auto_install': True,
    'installable': True,
 }
