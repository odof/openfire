# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Gestion des échantillons",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour e-commerce : Gestion des échantillons
==========================================================
- Crée automatiquement un article échantillon pour les articles sur lesquels est coché of_sample_available
- Ajoute une séquence pour les échantillons
- Ajoute un bouton de commande d'échantillon sur le shop
- Modifie le comportement du panier
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_website_sale',
    ],
    'data': [
        'data/ir_sequence.xml',
        'views/product_template.xml',
        'views/sale_order.xml',
        'templates/website_sale.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
