# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
    'name': u"OpenFire Projets - Activités et périodes planifiées",
    'version': "10.0.2.1.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "projet",
    'summary': u"OpenFire Projets - Activités et périodes planifiées",
    'description': u"""
Module OpenFire de planification des projets
============================================
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
        'of_project',
        'of_hr_timesheet',
        ],
    'data': [
        'views/account_views.xml',
        'views/of_periode_planifiee_views.xml',
        'views/of_project_planning_views.xml',
        'views/of_project_views.xml',
        'views/of_hr_timesheet_views.xml',
        'security/ir.model.access.csv',
        'hooks/hook_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
