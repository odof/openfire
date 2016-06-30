# -*- coding: utf-8 -*-
{
    'name': 'OpenFire / Configurateur de produits',
    'author': 'OpenFire',
    'version': '1.0',
    'category': 'Ventes',
    'description': u"""Module OpenFire qui ajoute un configurateur de produits au module OpenFire nomenclature.
""",
    'depends': ['of_product_nomenclature'],
    "data" : [
        'views/of_product_nomenclature_configurateur_view.xml',
        'security/ir.model.access.csv',
    ],
}
