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
    'name' : "OpenFire / Escomptes",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Module Fabricants OpenFire",
    'summary': u"Gestion des escomptes",
    'description': u"""
Module OpenFire / Escomptes
===========================
Ce module permet l'impression de factures avec les escomptes résumés. 

Fonctionnalités
----------------
 - Ajout d'un type 'escompte' dans les catégories d'article
 - L'article escompte n'est pas imprimé dans le corps des factures mais le montant est repris au niveau des totaux

""",
    'depends' : [
        'product',
        'of_sale',
        'of_kit',
        'of_sale_discount',
        'sale',
        'purchase',
    ],
    'data' : [
        'views/ofab_escompte_views.xml',
        'reports/ofab_escompte_reports_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:sorderttabstop=4:shiftwidth=4:
