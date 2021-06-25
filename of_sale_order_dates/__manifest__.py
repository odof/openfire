# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Dates sur Commandes de Vente",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Dates sur Commandes de Vente OpenFire
============================================

Ce module surcharge le module standard Dates sur Commandes de Vente
""",
    'depends': [
        'sale_order_dates',
        'of_sale_stock',
    ],
    'data': [
        'views/sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
