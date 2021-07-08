# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Contrat Custom - questionnaire",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Module de lien entre contrats et questionnaires",
    "description": u"""
OpenFire / Contrat custom - questionnaire
==========================================
Module de lien entre les modules of_contract_custom et of_questionnaire

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_contract_custom",
        "of_questionnaire",
        ],
    "category": "OpenFire",
    "data": [
        'views/of_planning_views.xml',
        ],
    'installable': False,
    'application': False,
    'auto_install': False,
}
