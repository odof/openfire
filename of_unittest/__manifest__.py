# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'OpenFire / Tests unitaires',
    'version': '10.0.1.0.0',
    'author': 'OpenFire',
    'license': 'AGPL-3',
    'website': 'www.openfire.fr',
    'category': 'Generic Modules/Formation Tests unitaires',
    'description': u"""
Module de démo pour la formation sur les tests unitaires
""",
    'depends': [
        'of_base',
        'of_sale',
        'of_crm',
    ],
    "external_dependencies": {
        "python": ['mock'],
        "bin": [],
    },
    'demo_xml': [],
    'data': [],
    'installable': True,
}
