# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Contrat Custom - Abonnement",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Ajout des contrats OpenFire",
    "description": u"""
Contrats OpenFire - Abonnement
==============================
Ajout le type de contrat abonnement:
 
Contrats :
----------

Contrat:
 - Nouveau type de contrat : abonnement

Ligne de contrat :
 - Nouvelle façon de facturer en fonction du type de contrat

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_contract_custom",
    ],
    "category": "OpenFire",
    "data": [
        'views/of_contract_custom_views.xml',
        'views/product_views.xml',
        'views/sale_views.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
