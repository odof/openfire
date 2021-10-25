# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Connecteur ventes",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Openfire",
    'license': '',
    'summary': u"Openfire Connecteur commandes de vente",
    'description': u"""
Module OpenFire / Connecteur commandes de vente
===============================================

Module permettant la réception automatisée des commandes de vente depuis une base OpenFire.

/!\\\\ Information OpenFire :
Ce module nécessite l'installation de openerplib sur le serveur : sudo easy_install openerp-client-lib
""",
    'depends': [
        'of_sale',
    ],
    'data': [
        'views/partner_views.xml',
        'views/sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}