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
    'name' : "OpenFire / Secteur",
    'version' : "0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "",
    'summary': u"Ajout des secteur",
    'description': u"""
Module OpenFire / Secteur
===============================
Ce module ajoute la notion de secteur

""",
    'depends' : ["of_service_parc_installe"],
    'data' : [
        'views/of_secteur_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}