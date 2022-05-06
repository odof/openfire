# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#    Copyright © 2004-2016 Odoo S.A. License GNU LGPL
#
##############################################################################

{
    'name': "OpenFire / Arborescence articles",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "product",
    'summary': u"OpenFire / Arborescence articles",
    'description': u"""
Module OpenFire / Arborescence articles
=======================================
Ce module créer un nouvel objet catégorie de recherche pour créer l'arborescence des articles 
qui ne pointerait pas vers la catégorie interne, et permettre ainsi une plus grande flexibilité

Modifications
-------------
- Création d'un nouveau modèle de donnée catégorie de recherche
""",
    'depends': [
        'of_product',
        'of_sale',
        'app_product_superbar',
        'app_product_ztree',
        ],
    'data': [
        'views/of_product_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
