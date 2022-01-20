# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Connecteur common - sale/purchase",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Openfire",
    'summary': u"Openfire Connecteur ",
    'description': u"""
Module OpenFire / Connecteur common sale/purchase
===================================
Module fournissant des champs/fonctionnalitées communes aux modules of_datastore_sale et of_datastore_purchase
""",
    'depends': [
        'of_datastore_connector',
        'of_sale',
        'purchase',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
