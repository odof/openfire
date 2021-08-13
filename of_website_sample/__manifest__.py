# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Gestion des échantillons",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour e-commerce : Gestion des échantillons
===============================

""",
    'website': "www.openfire.fr",
    'depends': [
        'website_sale',
    ],
    'data': [
        'views/product_template.xml',
        'views/sale_order.xml',
        'templates/website_sale.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
