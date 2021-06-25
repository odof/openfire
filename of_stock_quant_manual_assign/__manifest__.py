# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Réservation manuelle des Quants",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Réservation manuelle des Quants OpenFire
===============================================

Ce module surcharge le module OCA Réservation manuelle des Quants
""",
    'depends': [
        'stock_quant_manual_assign',
        'of_stock',
    ],
    'data': [
        'views/stock_views.xml',
        'wizards/assign_manual_quants_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
