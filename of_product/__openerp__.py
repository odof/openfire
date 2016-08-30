# -*- coding: utf-8 -*-
{
    "name" : "OpenFire / Produits (articles)",
    "version" : "0.9",
    "author" : "OpenFire",
    "website" : "openfire.fr",
    "category" : "Generic Modules/Sales & Purchases",
    "description": """
Module produits OpenFire.
======================================

Ce module apporte une personnalisation des produits :

- Ajout champ Frais de port pour chaque article
""",
    "depends" : [
        'product',
    ],
    "demo_xml" : [ ],
    'data': [
        'views/of_product_view.xml',
    ],
    "installable": True,
    'active': False,
}

