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
    'name' : "OpenFire - Liste de prix",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Module Fabricants OpenFire",
    'summary': u"Gestion des Listes de prix",
    'description': u"""
Module OpenFire - Liste de prix
===============================
Ce module modifie le fonctionnement des listes de prix.

Fonctionnalités
----------------
 - Ajout du critère de marque comme critère de liste de prix
 - Ajout d'un calcul par coefficient sur les listes de prix
 - Ajout de la possibilité de calculer les prix de vente avec un coefficient (pa * coef = pv) sur les lignes de commandes de vente

""",
    'depends' : [
        'product',
        'sale',
        'of_product_brand',
    ],
    'data' : [
        'views/ofab_pricelist_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
