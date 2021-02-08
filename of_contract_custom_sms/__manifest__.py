# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Contrat Custom - sms",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Module de lien entre contrats et sms",
    "description": u"""
OpenFire / Contrat custom - sms
===============================
Module de lien entre les modules of_contract_custom et of_sms

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_contract_custom",
        "of_sms",
        ],
    "category": "OpenFire",
    "data": [
        'views/of_planning_views.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
