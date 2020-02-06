# -*- coding: utf-8 -*-

{
    "name": u"OpenFire / Unités de conditionnement",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    "description": u"""
Gestion des unités de conditionnement des articles.
""",
    "website": "www.openfire.fr",
    "depends": [
        'product',
        'sale',
        'stock',
        'sale_stock',
    ],
    "category": "OpenFire",
    "data": [
        'views/of_conditionnement_views.xml',
        'reports/of_report_delivery.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
