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
        'of_sale',
        'of_account_tax',
        'of_website_portal',
    ],
    'data': [
        'security/of_website_sale_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/product_views.xml',
        'views/payment_views.xml',
        'views/templates.xml',
        'views/res_config_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
