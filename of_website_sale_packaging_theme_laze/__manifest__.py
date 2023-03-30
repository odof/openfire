# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": u"OpenFire / eCommerce / Unités de conditionnement / Theme Laze",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    "description": u"""
Gestion des unités de conditionnement des articles sur le e-commerce avec le thème Laze.
""",
    "website": "www.openfire.fr",
    "depends": [
        'of_website_sale_packaging',
        'theme_laze',
    ],
    "category": "OpenFire",
    "data": [
        'views/template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
