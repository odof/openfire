# -*- encoding: utf-8 -*-

{
    "name" : "OpenFire / Fournisseur de produits",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "website" : "http://www.openfire.fr",
    "category" : "Generic Modules",
    "description": u"""
Module OpenFire pour bases de centralisation des tarifs.
========================================================

""",
    "depends" : ['of_product', 'of_product_brand', 'of_sales', 'account'],
    "init_xml" : [],
    "demo_xml" : [],
    "data" : [
        'security/ir.model.access.csv',
#        'of_datastore_supplier_view.xml',
#        'of_datastore_supplier_data.xml',
    ],
    "installable": True,
    'active': False,
}
