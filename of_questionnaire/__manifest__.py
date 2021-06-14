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
    'name' : "OpenFire / Questionnaire",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "questionnaire",
    'summary': u"Ajout des questionnaires",
    'description': u"""
Module OpenFire - Questionnaire
===============================
Ce module ajoute les questionnaires d'intervention et d'équipement

Fonctionnalités
----------------
 - Ajout des questionnaire avec 2 types disponibles (intervention et équipement)
 - Permet de choisir un questionnaire par défaut sur un modèle d'intervention
 - Permet la sélection d'un questionnaire sur les interventions (les questions du questionnaire sont copiées dans l'intervention)
""",
    'depends' : [
        'of_planning',
        'of_service_parc_installe',
        ],
    'data' : [
        'views/of_questionnaire_views.xml',
        'views/of_planning_intervention_template_views.xml',
        'report/of_questionnaire_fiche_intervention.xml',
        'security/ir.model.access.csv',
        'wizards/of_questionnaire_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
