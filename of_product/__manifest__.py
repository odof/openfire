# -*- coding: utf-8 -*-
{
    'name' : "OpenFire / Produits (articles)",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "openfire.fr",
    'category' : "Generic Modules/Sales & Purchases",
    'description': """
Module produits OpenFire.
=========================

Ce module apporte une personnalisation des produits :
 - Mettre par défaut la référence produit (default_code) de l'article de base lors de la création d'une variante
 - Ajout des champs 'modele', 'marge', 'description_fabricant' et 'date_tarif' dans product.template
 - Ajout des champs 'old_code', 'pp_ht' et 'remise' dans product.supplierinfo
""",
    'depends' : [
        'product',
    ],
    'data': [
        'views/of_product_views.xml',
    ],
    'installable': True,
}
