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
    "depends" : ['of_product', 'of_product_brand', 'of_sale', 'account', 'of_import'],
    "init_xml" : [],
    "demo_xml" : [],
    "data" : [
        'views/of_datastore_supplier_views.xml',
    ],
    "installable": True,
    'active': False,
}
