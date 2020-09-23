# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Point de Vente",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Point de Vente OpenFire
==============================

Ce module apporte une personnalisation des points de ventes
""",
    'depends': [
        'point_of_sale',
        'of_account_payment_mode',
    ],
    'data': [
        'views/account_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
