# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Connecteur commun - achats/ventes",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Openfire",
    'summary': u"Openfire Connecteur commun - achats/ventes",
    'description': u"""
Module OpenFire / Connecteur commun - achats/ventes
===================================================
Module fournissant des champs/fonctionnalités communs aux modules of_datastore_sale et of_datastore_purchase
""",
    'depends': [
        'of_datastore_connector',
        'of_sale',
        'purchase',
        'of_stock',
    ],
    'data': [
        'views/purchase_views.xml',
        'views/picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
