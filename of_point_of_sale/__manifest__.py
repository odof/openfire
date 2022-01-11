# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Point de Vente",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Point de Vente OpenFire
==============================

Ce module apporte une personnalisation des points de ventes.

ATTENTION, pour pouvoir installer ce module, il faut au préalable définir des valeurs par défaut pour 
les champs marque ('brand_id') et catégorie interne ('categ_id') des articles (modèle 'product.template').
""",
    'depends': [
        'point_of_sale',
        'of_account_payment_mode',
        'of_account_tax',
        'of_tiers',
    ],
    'data': [
        'views/account_views.xml',
        'views/product_views.xml',
        'views/pos_views.xml',
        'views/templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
