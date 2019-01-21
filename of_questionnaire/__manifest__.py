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
    'name' : "OpenFire - Questionnaire",
    'version' : "0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "A REMPLACER",
    'summary': u"A REMPLACER",
    'description': u"""
Module OpenFire - Questionnaire
===============================
Ce module modifie/Ajoute

Fonctionnalités
----------------
 - 
""",
    'depends' : [
        'of_planning',
        'of_parc_installe',
        ],
    'data' : [
        'views/of_questionnaire_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}