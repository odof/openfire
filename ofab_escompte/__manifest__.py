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
    'name': "OpenFire / Escomptes",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Module Fabricants OpenFire",
    'summary': u"Gestion des escomptes",
    'description': u"""
Module OpenFire / Escomptes
===========================
Ce module permet l'impression de factures avec les escomptes résumés.

Fonctionnalités
----------------
 - Ajout d'un type 'escompte' dans les catégories d'article

""",
    'depends': [
        'product',
        'of_sale',
        'of_kit',
        'of_sale_discount',
        'sale',
        'purchase',
    ],
    'data': [
        'views/ofab_escompte_views.xml',
        'reports/ofab_escompte_reports_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
