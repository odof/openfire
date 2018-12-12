# -*- coding: utf-8 -*-

{
    "name" : "OpenFire / Products brands",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "website" : "http://www.openfire.fr",
    "category" : "Generic Modules",
    "license": "AGPL-3",
    "description": """
OpenFire module to manage products brand
========================================

""",
    "depends" : [
        'of_product',
        'sale',
    ],
    "init_xml" : [],
    "demo_xml" : [],
    "data" : [
        'security/ir.model.access.csv',
        'wizards/of_product_brand_add_products.xml',
        'views/of_product_brand_view.xml',
        'report/of_sale_report_view.xml',
        'report/of_account_report_views.xml',
    ],
    "installable": True,
}
