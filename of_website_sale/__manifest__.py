# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / E-commerce",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour e-commerce
===============================

""",
    'website': "www.openfire.fr",
    'depends': [
        'website_sale',
        'website_sale_options',
        'of_account_tax',
    ],
    'data': [
        'views/product_views.xml',
        'views/templates.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
