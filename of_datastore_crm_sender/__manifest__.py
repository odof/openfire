# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Connecteur CRM - Base mère",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Openfire",
    'license': '',
    'summary': u"Openfire Connecteur CRM - Base mère",
    'description': u"""
Module OpenFire / Connecteur CRM - Base mère
============================================

Module permettant l'envoi automatisé des opportunités vers des bases OpenFire.

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
        'data/of_datastore_crm_sender_data.xml',
        'security/crm_security.xml',
        'wizards/of_datastore_crm_sender_allocate_wizard_views.xml',
        'views/of_datastore_crm_sender_views.xml',
        'views/crm_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
