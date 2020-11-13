# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Marge sur les factures",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Marge sur les factures OpenFire
======================================

Ce module apporte la notion de marge sur les factures client
""",
    'depends': [
        'of_purchase',
        'of_sale',
        'of_account',
        'of_kit',
    ],
    'data': [
        'views/account_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
