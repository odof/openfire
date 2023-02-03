# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Groupes de comptes",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'category': u"Accounting",
    'description': u"""
Module OpenFire pour les groupes de comptes comptables
======================================================

- Permet de spécifier plusieurs préfixes pour un même groupe, séparés par des virgules.
- Permet de restreindre un groupe à un ou plusieurs types de comptes.
""",
    'website': "www.openfire.fr",
    'depends': [
        'account_group',
    ],
    'data': [
        'data/of_account_group_data.xml',
        'security/ir.model.access.csv',
        'views/of_account_group_views.xml',
    ],
    'installable': True,
}
