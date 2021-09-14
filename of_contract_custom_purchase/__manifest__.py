# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Contrat Custom - Achats",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Module de lien entre contrats et achats",
    "description": u"""
OpenFire / Contrat custom - Achats
==================================

Module de lien entre les modules of_contract_custom et of_purchase

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_contract_custom",
        "of_purchase",
        ],
    "category": "OpenFire",
    "data": [
        'views/of_service_views.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
