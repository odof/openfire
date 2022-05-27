# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Rapprochements bancaires",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'category': 'OpenFire',
    "description": """
Module OpenFire des rapprochements bancaires
============================================

Permet le pointage des écritures bancaires.
""",
    "website": "www.openfire.fr",
    "depends": [
        "account",
        "of_base_multicompany",
    ],
    "data": [
        'views/of_account_bank_reconciliation_views.xml',
        'security/ir.model.access.csv',
        'security/of_account_bank_reconciliation_security.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
