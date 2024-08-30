# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Réseau Commercial",
    'version': '10.0.1.1.0',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'summary': u"Réseau Commercial",
    'license': 'AGPL-3',
    'description': u"""
Application Réseau Commercial
=============================
""",
    'website': u"www.openfire.fr",
    'depends': [
        'sales_team',
    ],
    'data': [
        'views/of_sales_network_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
}
