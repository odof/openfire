# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Connecteur achats",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Openfire",
    'license': '',
    'summary': u"Openfire Connecteur commandes d'achat",
    'description': u"""
Module OpenFire / Connecteur commandes d'achat
==============================================

Module permettant l'envoi automatisé des commandes d'achat vers une base OpenFire.

/!\\\\ Information OpenFire :
Ce module nécessite l'installation de openerplib sur le serveur : sudo easy_install openerp-client-lib
""",
    'depends': [
        'of_purchase',
        'of_datastore_connector',
    ],
    'data': [
        'views/of_datastore_purchase_views.xml',
        'views/purchase_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
