# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Echantillons / Produits Optionnels",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour e-commerce : Module intermédiaire entre la gestion des échantillons et les produits optionnels
==========================================================
- Empêche l'ajout en panier d'un article quand c'est un panier échantillon
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_website_sample',
        'website_sale_options',
    ],
    'data': [
        'templates/website_sale.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
