# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Products brands",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    "website": "http://www.openfire.fr",
    "category": "OpenFire",
    "license": "AGPL-3",
    "description": """
OpenFire module to manage products brand
========================================

""",
    "depends": [
        'of_product',
        'sale',
    ],
    "init_xml": [],
    "demo_xml": [],
    "data": [
        'data/of_product_brand_data.xml',
        'security/of_product_brand_security.xml',
        'security/ir.model.access.csv',
        'wizards/of_product_brand_add_products.xml',
        'views/of_product_brand_view.xml',
        'views/res_user_views.xml',
        'report/of_sale_report_view.xml',
        'report/of_purchase_report_views.xml',
        'report/of_account_report_views.xml',
    ],
    "installable": True,
}
