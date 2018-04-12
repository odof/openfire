# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS sous licence AGPL-3.0
#
#    Compatible avec Odoo 10 Community Edition
#    Copyright © 2004-2016 Odoo S.A. License GNU LGPL
#
##############################################################################

{
    'name' : "OpenFire - Categories Feuilles de Temps",
    'version' : "10.0.1.0.0",
    'license': 'AGPL-3',
    'author' : "OpenFire",
    'website' : "https://www.openfire.fr",
    'category': "Module OpenFire - Employés",
    'complexity': "",
    'summary': u"""Feuilles de Temps par categories""",
    'description': u"""
Module OpenFire - Categories Feuilles de Temps
==============================================
Ce module permet la création de sous-catégories dans les feuilles de temps pour organiser un projet.

Fonctionnalités
---------------
- Configuration pour la création de catégories et sous-catégories
- Affichage de la catégorie dans les feuilles de temps et les activités détaillées
- Rapports par catégorie
- Recherche par catégorie
- Association des catégories aux projets et tâches
""",
    'depends' : [
        'hr_timesheet',
        'hr_timesheet_sheet',
        'project',
        'analytic',
    ],
    'data' : [
        'views/of_hr_timesheet_categories_views.xml',
        'security/ir.model.access.csv',
    ],
    'active': True,
    'installable': True,
    'application': False,
    'auto_install': False,
}