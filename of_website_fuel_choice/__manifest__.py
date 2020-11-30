# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Choix de combustible pour le site internet",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module intégrant un outil de choix de combustible pour le site internet
=======================================================================

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_utils',
        'of_website',
        'of_website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/of_website_product_fuel_views.xml',
        'views/templates.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
