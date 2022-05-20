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
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "projet",
    'summary': u"OpenFire Projets",
    'description': u"""
Module OpenFire Projets
=======================
Ce module modifie/ajoute des fonctionnalités aux projets

Modifications
-------------
- Dates de début/fin des tâches et projets
- Semaine de début du projet
- État du projet
- Étiquettes de projet
- Priorité du projet : Un projet avec 3 tâches importantes est prioritaire sur un projet qui n’en a qu’une
- Projet et catégorie obligatoires dans la tâche
- Le code de la tâche apparaît dans son nom
""",
    'depends': [
        'hr_timesheet',
        'of_base',
        'of_planning',
        'of_planning_tournee',
        'project',
        'project_timeline',
        'project_task_category',
        'project_task_dependency',
        'sale_order_project',
        # Dépendances servant uniquement à faciliter l'installation des modules
        'project_description',
        'project_parent',
        'project_stage_state',
        'project_task_add_very_high',
        'project_task_code',
        'project_task_default_stage',
        'project_team',
        ],
    'data': [
        'security/ir.model.access.csv',
        'security/of_project_security.xml',
        'views/of_project_views.xml',
        'views/of_sale_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_views.xml',
        'views/of_planning_intervention_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
