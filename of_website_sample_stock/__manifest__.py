# -*- coding: utf-8 -*-
{
    'name': 'OpenFire / Website Sample Stock',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Summary',
    'description': u"""
OpenFire / Website Sample Stock
===============================
""",
    'website': 'openfire.fr',
    'depends': [
        'of_website_sample',
        'website_sale_product_stock',
    ],
    'data': [
        'templates/website_sale.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'auto_install': True,
}
