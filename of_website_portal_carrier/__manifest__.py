# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Portail transporteur",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'description': u"""
Module OpenFire pour le portail transporteur du site internet
=============================================================

""",
    'website': u"www.openfire.fr",
    'depends': [
        'base',
        'of_website_portal',
        'of_stock',
    ],
    'data': [
        'security/of_website_portal_carrier_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/of_website_portal_carrier_views.xml',
        'views/res_config_settings_views.xml',
        'templates/template_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

