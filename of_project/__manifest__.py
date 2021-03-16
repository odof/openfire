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
    'name': "OpenFire Projets",
    'version': "0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "projet",
    'summary': u"OpenFire Projets",
    'description': u"""
Module OpenFire Projets
===============================
Ce module modifie/ajoute des fonctionnalités aux projets

Modifications
-------------
 - Ajout du choix de période planifié sur les tâches

Fonctionnalités
---------------
 - Ajout des périodes planifiées
    - Permet de définir un période de travail avec plusieurs utilisateurs
    - Définir le temps de travail de l'utilisateur et la répartition de ce temps de travail
 - Possibilité de répartir le temps prévu de la tache sur plusieurs périodes
""",
    'depends': [
        'project',
        'project_timeline',
        'project_task_category',
        'hr_timesheet',
        'of_base',
        'website_support',
        ],
    'data': [
        'data/of_project_data.xml',
        'views/of_project_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
