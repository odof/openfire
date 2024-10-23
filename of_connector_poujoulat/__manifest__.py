# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Connecteur Poujoulat",
    'author': u"OpenFire",
    'version': '10.0.1.0.0',
    'category': u"OpenFire modules",
    'description': u"""
Connecteur à la plateforme d'achats Poujoulat
=============================================

Ce module permet de transmettre une commande d'achat vers la plateforme d'achats de Poujoulat.

Les paramètres de connexion sont à configurer dans la partie Connecteurs / Configuration.

- of_poujoulat_host : Adresse du serveur
- of_poujoulat_partner_ids : [id des partenaire fournisseur Poujoulat] : ces id servent à idenfifier les commandes
  d'achat éligibles.
- of_poujoulat_brand_ids : [id des marques Poujoulat] : ces id servent à identifier les marques/articles éligibles
    """,
    'website': 'openfire.fr',
    'depends': [
        'of_base',
        'of_purchase',
        'of_product_brand',
        'of_utils',
    ],
    'data': [
        'data/of_sanitize_query.xml',
        'views/res_config_views.xml',
        'views/purchase_order_views.xml',
        'views/product_template.xml',
        'wizards/of_wizard_poujoulat_cart_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
