# -*- coding: utf-8 -*-
{
    'name' : "OpenFire / Produits (articles)",
    'version' : "0.9",
    'author' : "OpenFire",
    'website' : "openfire.fr",
    'category' : "Generic Modules/Sales & Purchases",
    'description': """
Module produits OpenFire.
======================================

Ce module apporte une personnalisation des produits :
- Mettre par défaut la référence produit (default_code) de l'article de base lors de la création d'une variante
""",
    'depends' : [
        'product',
    ],
    'data': [
        'views/of_product_view.xml',
    ],
    'installable': True,
}
