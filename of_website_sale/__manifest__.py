# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': u"OpenFire / E-commerce",
    'version': "10.0.2.1.1",
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
        'website_breadcrumb',
        'website_canonical_url',
    ],
    'data': [
        'security/of_website_sale_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/product_views.xml',
        'views/payment_views.xml',
        'views/templates.xml',
        'hooks/post_hook.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
