# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / API (Planning)",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': 'AGPL-3',
    'complexity': "easy",
    'description': u"""
Module d'API web OpenFire - Planning
====================================

Autorisation d'accès par l'API aux RDV et un certain nombre de leurs champs.

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_web_api',
        'of_planning',
        'of_sale_stock',
    ],
    'category': "OpenFire",
    'data': [
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
