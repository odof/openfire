# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Connecteur CRM - Base fille",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Openfire",
    'license': '',
    'summary': u"Openfire Connecteur commandes CRM - Base fille",
    'description': u"""
Module OpenFire / Connecteur commandes CRM - Base fille
=======================================================

Module permettant la réception automatisée des opportunités depuis une base OpenFire.

/!\\\\ Information OpenFire :
Ce module nécessite l'installation de openerplib sur le serveur : sudo easy_install openerp-client-lib
""",
    'depends': [
        'of_crm',
        'of_datastore_connector',
        'of_datastore_crm_stage',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/of_datastore_crm_data.xml',
        'views/crm_views.xml',
        'views/of_datastore_crm_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
