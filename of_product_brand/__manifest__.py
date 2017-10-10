# -*- encoding: utf-8 -*-

{
    "name" : "OpenFire / Products brands",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "website" : "http://www.openfire.fr",
    "category" : "Generic Modules",
    "description": """
OpenFire module to manage products brand
========================================

""",
    "depends" : ['product'],
    "init_xml" : [ ],
    "demo_xml" : [ ],
    "update_xml" : [
        'security/ir.model.access.csv',
        'views/of_product_brand_view.xml',
    ],
    "installable": True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
