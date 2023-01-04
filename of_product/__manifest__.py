# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Produits (articles)",
    'version': '10.0.1.1.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'website': u"openfire.fr",
    'category': u"Generic Modules/Sales & Purchases",
    'description': u"""
Module produits OpenFire.
=========================

Ce module apporte une personnalisation des produits :
 - Mettre par défaut la référence produit (default_code) de l'article de base lors de la création d'une variante
 - Ajout des champs 'modele', 'marge', 'description_fabricant' et 'date_tarif' dans product.template
 - Ajout des champs 'old_code', 'pp_ht' et 'remise' dans product.supplierinfo
""",
    'depends': [
        'product',
        'purchase',
        'of_utils',
    ],
    'data': [
        'security/of_product_security.xml',
        'security/ir.model.access.csv',
        'views/of_product_views.xml',
    ],
    'installable': True,
}
