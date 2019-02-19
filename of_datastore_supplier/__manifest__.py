# -*- coding: utf-8 -*-

{
    "name" : "OpenFire / Base centrale des articles",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "website" : "http://www.openfire.fr",
    "category" : "OpenFire",
    "description": u"""
Module OpenFire pour bases de centralisation des tarifs.
========================================================

Ajoute un champ de notes de mise à jour dans les marques.
""",
    "depends" : ['of_product', 'of_product_brand', 'of_import'],
    "init_xml" : [],
    "demo_xml" : [],
    "data" : [
        'views/of_datastore_supplier_views.xml',
    ],
    "installable": True,
}
