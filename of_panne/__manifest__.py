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
    'name' : "OpenFire / Panne",
    'version' : "0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "A REMPLACER",
    'summary': u"Panne",
    'description': u"""
Module OpenFire - Panne
===============================
Ce module ajoute l'utilisation des pannes

Fonctionnalités
----------------
 - 
""",
    'depends' : [
        'of_service_parc_installe',
        ],
    'data' : [
        'views/of_panne_views.xml',
        'wizard/of_panne_wizard_view.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}