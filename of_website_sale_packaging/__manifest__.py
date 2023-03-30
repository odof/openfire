# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": u"OpenFire / eCommerce / Unités de conditionnement",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    "description": u"""
Gestion des unités de conditionnement des articles sur le e-commerce.
""",
    "website": "www.openfire.fr",
    "depends": [
        'of_website_sale',
        'of_conditionnement',
    ],
    "category": "OpenFire",
    "data": [
        'views/asset_views.xml',
        'views/template_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
