# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Éco contribution",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'description': u"""
Gestion des Éco contributions
=============================
""",
    'website': u"www.openfire.fr",
    'depends': [
        'of_conditionnement',
    ],
    'category': u"OpenFire",
    'data': [
        'security/of_sale_stock_security.xml',
        'security/ir.model.access.csv',
        'views/of_eco_contribution_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
